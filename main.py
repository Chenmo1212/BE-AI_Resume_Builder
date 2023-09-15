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

    # Step 2 - read raw resume and create Resume builder object
    my_resume = Resume_Builder(
        resume=utils.read_yaml(filename=os.path.join(my_files_dir, raw_resume_file)),
        parsed_job=parsed_job,
        llm_kwargs=llm_kwargs,
    )
    projects = my_resume.projects_raw
    experiences = my_resume.experiences_raw
    skills = my_resume.skills_raw

    # Step 3 - Rephrase unedited experiences. Try re-running cells in case of missing answers or hallucinations.
    experiences = my_resume.rewrite_unedited_experiences(verbose=False)
    utils.write_yaml(dict(experiences=experiences))

    # Step 4 - Rephrase projects
    # my_resume.experiences = experiences

    # projects = my_resume.rewrite_projects_desc(verbose=False)
    # utils.write_yaml(dict(projects=projects))

    # Review the generated output in previous cell.
    # If any updates are needed, copy the cell output below between the triple quotes
    # Set value to """" """" if no edits are needed
    # edits = """ """
    #
    # edits = edits.strip()
    # if edits:
    #     edits2 = utils.read_yaml(edits)
    #     if "experiences" in edits2:
    #         experiences = edits2["experiences"]
    #     if "projects" in edits2:
    #         projects = edits2["projects"]
    #     if "skills" in edits2:
    #         skills = edits2["skills"]
    #     if "summary" in edits2:
    #         summary = edits2["summary"]

    # Step 5 - Extract skills
    # This will match the required skills from the job post with your resume sections
    # Outputs a combined list of skills extracted from the job post and included in the raw resume
    my_resume.experiences = experiences
    my_resume.projects = projects

    skills = my_resume.extract_matched_skills(verbose=False)
    utils.write_yaml(dict(skills=skills))

    # Review the generated output in previous cell.
    # If any updates are needed, copy the cell output below between the triple quotes
    # Set value to """" """" if no edits are needed
    edits = """ """

    edits = edits.strip()
    if edits:
        edits3 = utils.read_yaml(edits)
        if "experiences" in edits3:
            experiences = edits3["experiences"]
        if "projects" in edits3:
            projects = edits3["projects"]
        if "skills" in edits3:
            skills = edits3["skills"]
        if "summary" in edits3:
            summary = edits3["summary"]

    # Step 6 - Create a resume summary
    my_resume.experiences = experiences
    my_resume.skills = skills
    my_resume.projects = projects

    summary = my_resume.write_summary(
        verbose=True,
    )
    utils.write_yaml(dict(summary=summary))

    # Review the generated output in previous cell.
    # If any updates are needed, copy the cell output below between the triple quotes
    # Set value to """" """" if no edits are needed.
    edits = """ """

    edits = edits.strip()
    if edits:
        edits4 = utils.read_yaml(edits)
        if "experiences" in edits4:
            experiences = edits4["experiences"]
        if "projects" in edits4:
            projects = edits4["projects"]
        if "skills" in edits4:
            skills = edits4["skills"]
        if "summary" in edits4:
            summary = edits4["summary"]

    # Step 7 - Generate final resume yaml for review
    my_resume.summary = summary
    my_resume.experiences = experiences
    my_resume.projects = projects
    my_resume.skills = skills

    today_date = datetime.today().strftime("%Y%m%d")
    resume_filename = os.path.join(
        my_files_dir, sanitize_filename(f"{today_date}__{company_name}__{job_title}")
    )
    resume_final = my_resume.finalize()
    print(f"#filename: {resume_filename}.yaml\n")
    utils.write_yaml(resume_final, filename=f"{resume_filename}.yaml")

    # Step 8 - Identify resume improvements
    # A previously generated resume can also be used here by manually providing resume_filename. Requires the associated parsed job file.
    final_resume = Resume_Builder(
        resume=utils.read_yaml(filename=f"{resume_filename}.yaml"),
        parsed_job=utils.read_yaml(filename=f"{resume_filename}.job"),
        is_final=True,
        llm_kwargs=llm_kwargs,
    )
    improvements = final_resume.suggest_improvements(verbose=True)
    utils.write_yaml(dict(improvements=improvements))

    # Step 9 - Generate pdf from yaml
    # Most common errors during pdf generation occur due to special characters. Escape them with backslashes in the yaml, e.g. $ -> \$
    # pdf_file = utils.generate_pdf(yaml_file=f"{resume_filename}.yaml")
    # display(Markdown((f"[{pdf_file}](<{pdf_file}>)")))
    utils.generate_new_tex(yaml_file=f"{resume_filename}.yaml")
