"""
Improved multi-job render script using common utilities
"""

import sys
import os
import time
import json
import tkinter as tk
from tkinter import filedialog
import unreal

# Add the common directory to Python path
common_dir = os.path.dirname(os.path.abspath(__file__))
if common_dir not in sys.path:
    sys.path.append(common_dir)

from render_queue_validation import UE5RenderUtils


class UE5MultiJobRenderer:
    """Handles multi-job rendering with proper state management"""
    
    def __init__(self):
        self.utils = UE5RenderUtils()
        self.mrq_subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
        self.executor = unreal.MoviePipelinePIEExecutor(self.mrq_subsystem)
        self.pipeline_queue = self.mrq_subsystem.get_queue()
        
        # State management
        self.current_job_index = 0
        self.current_render_index = 0
        self.current_pano_points = []
        self.current_level_name = ""
        self.base_output_dir = ""
        
        # Bind callbacks
        self.executor.on_executor_finished_delegate.add_callable_unique(self._on_render_finished)
        self.executor.on_executor_errored_delegate.add_callable_unique(self._on_render_error)
    
    def set_user_exposed_variable_path(self, job: unreal.MoviePipelineExecutorJob, path: str):
        """Set output directory for the job"""
        graph = job.get_graph_preset()
        variables = graph.get_variables()

        if not variables:
            unreal.log_warning("No variables are exposed on this graph, expose 'OutputDirectory' to set custom paths")
            return False

        for variable in variables:
            if variable.get_member_name() == "OutputDirectory":
                variable_assignment = job.get_or_create_variable_overrides(graph)
                variable_assignment.set_value_serialized_string(variable, unreal.DirectoryPath(path).export_text())
                variable_assignment.set_variable_assignment_enable_state(variable, True)
                return True
        
        unreal.log_warning("OutputDirectory variable not found in job variables")
        return False
        
    def scopeout_output_dir(self):
        if not self.base_output_dir:
            unreal.log_error("No output directory selected. Exiting...")
            return False

        if not os.path.isdir(self.base_output_dir):
            try:
                os.mkdir(self.base_output_dir)
                
            except:
                unreal.log_error("Could not create output directory. Exiting...")
                return False

        self.progress_cache_file_path = os.path.join(self.base_output_dir, "render_progress_cache.json")
        validation_cache_file_path = os.path.join(self.base_output_dir, "validation_cache.json")

        if not os.listdir(self.base_output_dir):
            self.validate_cache()
            return True
        
        if os.path.isfile(validation_cache_file_path):
            if os.path.isfile(self.progress_cache_file_path):
                if not self.load_progress_cache():
                    unreal.log_warning("Progress Cache File not found, starting from begining")
                    return False
                
            return self.validate_cache()
        
        unreal.log_error("Invalid Folder")
        return False



    def load_progress_cache(self):
        
        with open(self.progress_cache_file_path, "r") as progress_cache_file:
            try:
                progress_cache = json.load(progress_cache_file)
                self.current_job_index = progress_cache["job_index"]
                self.current_render_index = progress_cache["pano_render_index"]

                return True
            except json.JSONDecodeError:
                unreal.log_warning("progress_cache file is not valid JSON. Initializing empty progress_cache.")
                return False
        unreal.log_error("Progress Cache file could not be read due to unknown error")
        return False
        
    
    def write_progress_cache(self):
        progress_cache = {
            "job_index": self.current_job_index,
            "pano_render_index": self.current_render_index
        }

        with open(self.progress_cache_file_path,'w') as progress_cache_file:
            json.dump(progress_cache, progress_cache_file, indent=4)
    


    def validate_cache(self):
        validation_cache_file_path = os.path.join(self.base_output_dir, "validation_cache.json")
        if not os.path.isfile(validation_cache_file_path):
            unreal.log("Writing new Validation Data...")
            with open(validation_cache_file_path, "w") as validation_cache_file:
                json.dump(self.validation_data,validation_cache_file,indent = 4)
            return True
        
        with open(validation_cache_file_path, "r") as validation_cache_file:
            try:
                validation_cache = json.load(validation_cache_file)
            except json.JSONDecodeError:
                unreal.log_warning("validation_cache file is not valid JSON. Initializing empty validation_cache.")
                return False

        
        if self.validation_data != validation_cache:
            ##### Return True if validation data till progress is same, overwrite new validation
            unreal.log_error("Validation cache does not match current queue")
            return False
        unreal.log("Validation cache checked, same as current queue.")

        return True
 

    
    def select_output_directory(self):
        """Show directory picker and set base output directory"""
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        
        self.base_output_dir = filedialog.askdirectory(title="Select an output folder")
        root.destroy()
        
        if not self.base_output_dir:
            unreal.log_error("No output directory selected. Exiting...")
            return False
        
        unreal.log(f"Output directory set to: {self.base_output_dir}")
        return True
    
    def start_rendering(self):
        """Start the multi-job rendering process"""
        isQueueValid, validation_data, _  = self.utils.validate_movie_render_queue()
        if not isQueueValid:
            return False
        self.validation_data = validation_data
        

        if not self.select_output_directory():
            return False
        
        if not self.scopeout_output_dir():
            return False
        
        
        unreal.log(f"Starting render process with {len(self.pipeline_queue.get_jobs())} jobs")
        self._process_next_job()
        return True
    


    def _process_next_job(self):
        """Process the next job in the queue"""
        unreal.log(f"Processing next job {self.current_job_index + 1}/{len(self.pipeline_queue.get_jobs())}")
        self.write_progress_cache()
        if self.current_job_index >= len(self.pipeline_queue.get_jobs()):
            unreal.log("All jobs completed!")
            self._cleanup()
            return
        
        self.current_job = self.pipeline_queue.get_jobs()[self.current_job_index]
        unreal.log(f"Processing job {self.current_job_index + 1}/{len(self.pipeline_queue.get_jobs())}: {self.current_job.job_name}")
        
        # Validate job using common utilities
        is_valid, level_name, job_comment, pano_point_names = self.utils.validate_render_job(self.current_job)
        
        if not is_valid:
            unreal.log_error(f"Job {self.current_job.job_name} failed validation. Skipping...")
            self.current_job_index += 1
            self._process_next_job()
            return
        
        self.current_level_name = level_name
        
        # Get actors from the loaded level
        self.current_pano_points = sorted([actor for actor in self.utils.eas.get_all_level_actors() 
                                          if actor.get_class() == self.utils.pano_point_class],
                                         key=lambda a: a.get_actor_label())
        
        cameras = sorted([actor for actor in self.utils.eas.get_all_level_actors() 
                         if actor.get_class() == self.utils.camera_class],
                        key=lambda a: a.get_actor_label())
        
        self.current_camera = cameras[0]
        
        if not self.current_camera:
            unreal.log_error(f"VeroCineCam not found in level {level_name}")
            self.current_job_index += 1
            self._process_next_job()
            return
        
        # Disable all jobs except current one
        for job in self.pipeline_queue.get_jobs():
            job.set_is_enabled(job == self.current_job)
        
        # Start rendering pano points for this job
        self.current_render_index = 0
        self._render_next_pano_point()
    
    def _render_next_pano_point(self):
        """Render the next pano point in the current job"""
        
        self.write_progress_cache()
        if self.current_render_index >= len(self.current_pano_points):
            # All pano points for this job are done, move to next job
            self.current_job_index += 1
            self._process_next_job()
            return
        
        pano_point = self.current_pano_points[self.current_render_index]
        unreal.log(f"Job Index : {self.current_job_index}. Rendering pano point {self.current_render_index + 1}/{len(self.current_pano_points)}: {pano_point.get_actor_label()}")
        
        # Set pano point in camera
        
        self.current_camera.set_editor_property("PanoPoint", pano_point)
        
        # Set output directory
        pano_name = "".join(x for x in pano_point.get_actor_label().replace(" ", "_") 
                           if x.isalnum() or x in "_-")
        output_dir = unreal.Paths.combine([
            self.base_output_dir, "renders", 
            "_".join([str(x) for x in [self.current_level_name, pano_name, self.current_job.comment]])
        ])
        
        # Set output path in job
        if not self.set_user_exposed_variable_path(self.current_job, output_dir):
            unreal.log_error(f"Failed to set output directory for {pano_name}")
            self.current_render_index += 1
            self._render_next_pano_point()
            return
        
        # Enable job and start render
        self.current_job.set_is_enabled(True)
        self.mrq_subsystem.render_queue_with_executor_instance(self.executor)
        
        unreal.log(f"Started render for {pano_name} -> {output_dir}")
    
    def _on_render_finished(self, executor: unreal.MoviePipelineExecutorBase, success: bool):
        """Callback when render finishes"""
        if success:
            pano_point = self.current_pano_points[self.current_render_index]
            unreal.log(f"Successfully rendered: {pano_point.get_actor_label()}")
        else:
            unreal.log_error(f"Render failed for pano point {self.current_render_index}")
        
        # Move to next pano point
        self.current_render_index += 1
        self._render_next_pano_point()
    
    def _on_render_error(self, executor: unreal.MoviePipelineExecutorBase, pipeline: unreal.MoviePipeline, is_fatal: bool, error_text: str):
        """Callback when render encounters an error"""
        unreal.log_error(f"Render error: {error_text}")
        
        if is_fatal:
            unreal.log_error("Fatal error encountered. Stopping render process.")
            self._cleanup()
        else:
            # Try to continue with next pano point
            self.current_render_index += 1
            self._render_next_pano_point()
    
    def _cleanup(self):
        """Clean up resources and reset state"""
        # Remove callbacks
        self.executor.on_executor_finished_delegate.remove_callable(self._on_render_finished)
        self.executor.on_executor_errored_delegate.remove_callable(self._on_render_error)
        
        # Re-enable all jobs
        for job in self.pipeline_queue.get_jobs():
            job.set_is_enabled(True)
        
        unreal.log("Render process completed and cleaned up")


def main():
    """Main function to start the rendering process"""
    renderer = UE5MultiJobRenderer()
    
    # Start rendering
    return renderer.start_rendering()


if __name__ == "__main__":
    main()