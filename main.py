import os
from datetime import datetime
from IPython.display import display, Markdown
from pathvalidate import sanitize_filename

import utils

from prompts import Job_Post, Resume_Builder

if __name__ == '__main__':
    ## Inputs
    my_files_dir = "my_applications"  # location for all job and resume files
    job_file = "job.txt"  # filename with job post text. The entire job post can be pasted in this file, as is.
    raw_resume_file = "resume_raw.yaml"  # filename for raw resume yaml. See example in repo for instructions.

    # Model for matching resume to job post (except extraction chains)
    # gpt-4 is not publicly available yet and can be 20-30 times costlier than the default model gpt-3.5-turbo.
    # Simple extraction chains are hardcoded to use the cheaper gpt-3.5 model.
    # openai_model_name = "gpt-4"
    openai_model_name = "gpt-3.5-turbo"

    # temperature lower than 1 is preferred. temperature=0 returns deterministic output
    temperature = 0.5

    llm_kwargs = dict(
        model_name=openai_model_name,
        model_kwargs=dict(top_p=0.6, frequency_penalty=0.1),
    )

    # Step 1 - Read and parse job posting
    job_post = Job_Post(
        utils.read_jobfile(os.path.join(my_files_dir, job_file)),
    )
    parsed_job = job_post.parse_job_post(verbose=False)

    company_name = parsed_job["company"]
    job_title = parsed_job["job_title"]
    today_date = datetime.today().strftime("%Y%m%d")
    job_filename = os.path.join(
        my_files_dir, sanitize_filename(f"{today_date}__{company_name}__{job_title}")
    )
    print(f"#filename: {job_filename}.job\n")
    utils.write_yaml(parsed_job, filename=f"{job_filename}.job")
