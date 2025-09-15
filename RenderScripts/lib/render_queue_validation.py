"""
Common utilities for UE5 automation scripts
Shared functions for Movie Render Queue validation and level management
"""

import unreal

# Constants that might be shared across scripts
VALID_JOB_TYPES = ["DF", "DU", "NF", "NU"]
PANO_POINT_BLUEPRINT_PATH = "/Game/render_utils/BP/BP_PanoPoint"
CAMERA_BLUEPRINT_PATH = "/Game/render_utils/BP/VeroCineCam"

class UE5RenderUtils:
    """Common utilities for UE5 rendering and validation"""
    
    def __init__(self):
        # Initialize subsystems
        self.les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        self.eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.mrq_subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
        
        # Load common classes
        self.pano_point_class = unreal.load_asset("/Game/render_utils/BP/BP_PanoPoint").generated_class()
        self.camera_class = unreal.load_asset("/Game/render_utils/BP/VeroCineCam").generated_class()
    
    def validate_render_job(self, job: unreal.MoviePipelineExecutorJob):
        """
        Validate a single render job
        
        Args:
            job: MoviePipelineExecutorJob to validate
            
        Returns:
            tuple: (is_valid, level_name, job_comment, pano_point_names)
        """
        unreal.log(f"Validating job: {job.job_name}")
        null_return = (False, None, None, [])
        
        if not job:
            return null_return
        
        if not job.map:
            return null_return
        
        ln = ".".join(job.map.export_text().split(".")[:-1])

        if not job.sequence.export_text() or job.sequence.export_text().strip() == "None":
            unreal.log_error(f"Job {job.job_name} does not have a valid sequence. Exiting...")
            return null_return
        
        if not job.comment or job.comment.strip() not in ["DF", "DU", "NF", "NU"]:
            return null_return

        if self.les.load_level(ln):
            unreal.log(f"Level {ln} loaded successfully")
            level_name = ln.split("/")[-1]
        else:
            unreal.log_error(f"Failed to load level {ln}. Exiting...")
            return null_return      

        pano_points = sorted([actor for actor in self.eas.get_all_level_actors() 
                             if actor.get_class() == self.pano_point_class],
                            key=lambda a: a.get_actor_label())
        pano_point_names = sorted(list({p.get_actor_label() for p in pano_points}))
        
        # Find your camera (assuming there's one VeroCineCam in the scene)
        cameras = sorted([actor for actor in self.eas.get_all_level_actors() 
                         if actor.get_class() == self.camera_class],
                        key=lambda a: a.get_actor_label())
        camera = cameras[0] if cameras else None
        if not camera:
            unreal.log_error(f"VeroCineCam not found in level {level_name}")
            return null_return
        
        return True, level_name, job.comment, pano_point_names

    def validate_movie_render_queue(self):
        """
        Validate if Movie Render Queue is available and ready
        
        Returns:
            bool: True if queue is valid, False otherwise
        """
        null_return = False, {}, {}
        if not self.mrq_subsystem:
            unreal.log_error("Movie Render Queue subsystem not found. Please ensure it is enabled in the project settings.")
            return null_return
            
        pipeline_queue = self.mrq_subsystem.get_queue()
        if not pipeline_queue:
            unreal.log_error("Movie Render Queue is empty. Please add jobs to the queue.")
            return null_return
        
        if not pipeline_queue.get_jobs():
            unreal.log_error("No jobs found in the Movie Render Queue. Please add jobs to the queue.")
            return null_return
            
        unreal.log(f"Movie Render Queue with {len(pipeline_queue.get_jobs())} jobs is being validated.")

        validation_data = {"jobs": []}

        job_comment_dicts = {}

        job_name_level_dict = {}

        for i,job in enumerate(pipeline_queue.get_jobs()):
            valid, level_name, job_comment, pano_point_names = self.validate_render_job(job)
            if not valid:
                unreal.log_error(f"Job {job.job_name} is invalid. Please check the job settings.")
                return null_return
            else:
                unreal.log(f"Job {job.job_name} is valid with level {level_name}, comment {job_comment}, and pano points: {len(pano_point_names)}")
                if job_comment not in job_comment_dicts:
                    job_comment_dicts[job_comment] = []
                job_comment_dicts[job_comment].append((job.job_name, pano_point_names))

            validation_data["jobs"].append(
                {
                    "job_index": i,
                    "job_name": job.job_name,
                    "pano_points": "|".join(pano_point_names)
                }
            )
            job_name_level_dict[job.job_name] = job.map.export_text()
        unreal.log(", ".join([f"{k}: {len(v)} jobs" for k, v in job_comment_dicts.items()]))
        
        level_set_dict = {}
        

        for job_type, jobs in job_comment_dicts.items():
            for job_name, pano_points in jobs:
                pano_set_string = "|".join(pano_points)
                if pano_set_string not in level_set_dict:
                    level_set_dict[pano_set_string] = []
                level_set_dict[pano_set_string].append((job_name, job_type, job_name_level_dict[job_name], pano_points))

        
        
        unreal.log(", ".join([f"{v[0][0] if len(v) else 'Empty'}: {len(v)} jobs" for k, v in level_set_dict.items()]))

        
        
        for k in level_set_dict:
            if len(level_set_dict[k]) != 4:
                unreal.log_error(f"Job set does not have exactly 4 jobs. Please ensure each level has a job for each type (DF, DU, NF, NU).")
                unreal.log_error(f"Found {', '.join([v[0] for v in level_set_dict[k]])} jobs for pano set.")
                return null_return

            if not set(["DF", "DU", "NF", "NU"]).issubset(set([v[1] for v in level_set_dict[k]])):
                unreal.log_error(f"Job set does not have all required job types (DF, DU, NF, NU). Found: {', '.join([v[1] for v in level_set_dict[k]])}")
                return null_return

            # Example: collect the job name for the "DF" job type in this pano set
        
        validation_dict = {}
        for k in level_set_dict:
            jd = {}
            for ja in level_set_dict[k]:
                jd[ja[1]] = ja[0]
            jd['pano_points']= k

            validation_dict[jd["DF"]] = jd
            
        return True, validation_data, level_set_dict
    

# Convenience functions for backward compatibility or standalone use
def validate_render_job(job: unreal.MoviePipelineExecutorJob):
    """Standalone function wrapper for validate_render_job"""
    utils = UE5RenderUtils()
    return utils.validate_render_job(job)


def validate_movie_render_queue():
    """Standalone function wrapper for validate_movie_render_queue"""
    utils = UE5RenderUtils()
    return utils.validate_movie_render_queue()




if __name__ == "__main__":
    success, op, lsd = validate_movie_render_queue()

    for k, v in lsd.items():
        unreal.log(f"{',        '.join([f'{j[0]}:{j[2]} ({j[1]})' for j in v])}")
    unreal.log("__________________________________________________________")
    unreal.log(op)