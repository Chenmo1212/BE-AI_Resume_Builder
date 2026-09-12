import json
import logging
import os
import time
import asyncio
from datetime import datetime

import utils
from langchain_core.output_parsers import PydanticOutputParser
from llm.factory import create_llm
from chains.section_highlighter import build_section_highlighter_chain
from chains.skills_matcher import build_skills_matcher_chain
from chains.summary_writer import build_summary_writer_chain
from chains.improver import build_improver_chain
from chains.reviewer import build_reviewer_chain
from prompts import (
    Job_Description,
    Job_Skills,
    format_list_as_string,
    format_prompt_inputs_as_strings,
    datediff_years,
    ReviewerOutput,
)
from yaml_to_json import yaml_to_json

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, root_path="my_applications", openai_model_name="gpt-3.5-turbo", ai_config: dict = None):
        self.root_path: str = root_path
        self.raw_job: str = ""
        self.raw_resume: dict = {}
        self.final_resume: dict = {}
        self.parsed_job: dict = {}
        self.resume_builder: dict = {}
        self.resume_json: str = ""
        self.resume_filename: str = ""
        self.folder: str = ""
        self.ai_config: dict = dict(ai_config) if ai_config else {}

        # Pop sensitive fields immediately so they never appear in logs or DB writes.
        # Treat empty string as "not provided".
        _api_key = self.ai_config.pop("api_key", None) or None
        _base_url = self.ai_config.pop("base_url", None) or None

        provider = self.ai_config.get("provider")
        model = self.ai_config.get("model", openai_model_name)
        temperature = self.ai_config.get("temperature", 0.7)

        self.llm_kwargs = dict(
            provider=provider,
            model_name=model,
            temperature=temperature,
            api_key=_api_key,
            base_url=_base_url,
            model_kwargs=dict(top_p=0.6, frequency_penalty=0.1),
        )
        if provider is None:
            self.llm_kwargs.pop("provider")
        self._llm = None  # lazily initialized

    def _get_llm(self):
        if self._llm is None:
            self._llm = create_llm(**self.llm_kwargs)
        return self._llm

    def _active_sections(self) -> set:
        """Return the set of sections to process. Defaults to all four if not specified."""
        default = {"experience", "projects", "skills", "summary"}
        config = self.ai_config or {}
        sections = config.get("sections")
        if not sections:
            return default
        return {s.lower() for s in sections} & default

    def set_raw_resume(self, raw_resume=None, filename: str = ""):
        if raw_resume is None:
            raw_resume = {}
        if not raw_resume and not filename:
            logger.warning("Neither resume text nor filename have been provided.")
            return None
        if raw_resume:
            self.raw_resume = raw_resume
        else:
            self.raw_resume = utils.read_yaml(filename=filename)

    def set_job_text(self, job_text: str = "", filename: str = ""):
        if not job_text and not filename:
            logger.warning("Neither job text nor filename have been provided.")
            return None
        if job_text:
            self.raw_job = job_text
        else:
            self.raw_job = utils.read_jobfile(filename=filename)

    def _create_company_folder(self):
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

    def read_and_parse_job(self):
        logger.info("=========== Start parsing job information ===========")
        if not self.raw_job and not self.parsed_job:
            logger.warning("Job_text and Parsed_job are empty, please call set_job_text() first.")
            return None

        start_time = time.time()

        if not self.parsed_job:
            llm = self._get_llm()
            job_parser = PydanticOutputParser(pydantic_object=Job_Description)
            skills_parser = PydanticOutputParser(pydantic_object=Job_Skills)
            job_response = llm.invoke(
                f"Extract the job description from the following job posting.\n"
                f"{job_parser.get_format_instructions()}\n\n{self.raw_job}"
            )
            skills_response = llm.invoke(
                f"Extract the technical and non-technical skills from the following job posting.\n"
                f"{skills_parser.get_format_instructions()}\n\n{self.raw_job}"
            )
            parsed_job = job_parser.parse(getattr(job_response, "content", job_response))
            job_skills = skills_parser.parse(getattr(skills_response, "content", skills_response))
            if parsed_job and job_skills:
                self.parsed_job = {**parsed_job.model_dump(), **job_skills.model_dump()}

        company_name = self.parsed_job["company"]
        job_title = self.parsed_job["job_title"].replace("/", "_")
        today_date = datetime.today().strftime("%Y%m%d")
        company_folder_name = f"{today_date}__{company_name}__{job_title}"

        self.folder = os.path.join(self.root_path, company_folder_name)
        self._create_company_folder()
        job_filename = os.path.join(self.folder, job_title)
        job_filename, _ = os.path.splitext(job_filename)
        self.resume_filename = job_filename

        utils.write_yaml(self.parsed_job, filename=f"{self.resume_filename}.job")
        logger.info(f"Parsing done in {time.time() - start_time:.2f}s")

    def read_resume(self):
        logger.info("=========== Start reading resume ===========")
        if not self.parsed_job:
            self.read_and_parse_job()
        if not self.raw_resume:
            logger.warning("Resume_text is empty, please call set_resume_text() first.")
            return None
        # Initialize resume_builder as a dict holding processed sections
        self.resume_builder = {
            "basic_info": {
                **utils.get_dict_field(field="basics", resume=self.raw_resume),
                "label": self.parsed_job["job_title"],
            },
            "education": utils.get_dict_field(field="education", resume=self.raw_resume),
            "experiences_raw": utils.get_dict_field(field="work", resume=self.raw_resume),
            "projects_raw": utils.get_dict_field(field="projects", resume=self.raw_resume),
            "skills_raw": utils.get_dict_field(field="skills", resume=self.raw_resume),
            "summary_raw": utils.get_dict_field(field="summary", resume=self.raw_resume["basics"]),
            "achievements": utils.get_dict_field(field="achievements", resume=self.raw_resume.get("activities", {})),
            "experiences": None,
            "projects": None,
            "skills": None,
            "summary": "",
        }

    def _get_degrees(self) -> list:
        result = []
        for degrees in utils.generator_key_in_nested_dict("degrees", self.raw_resume):
            for degree in degrees:
                if isinstance(degree["names"], list):
                    result.extend(degree["names"])
                elif isinstance(degree["names"], str):
                    result.append(degree["names"])
        return result

    def _format_experiences_for_prompt(self, experiences: list) -> list:
        result = []
        for exp in experiences:
            curr = ""
            if "titles" in exp:
                exp_time = self._get_cumulative_time_from_titles(exp["titles"])
                curr += f"{exp_time} years experience in:"
            if "highlights" in exp:
                curr += format_list_as_string(exp["highlights"], list_sep="\n  - ")
                curr += "\n"
                result.append(curr)
        return result

    def _get_cumulative_time_from_titles(self, titles) -> int:
        result = 0.0
        last_date = ""
        for t in titles:
            if "startdate" in t and "enddate" in t:
                last_date = datetime.today().strftime("%Y-%m-%d") if t["enddate"] == "current" else t["enddate"]
                result += datediff_years(start_date=t["startdate"], end_date=last_date)
        return round(result)

    def _format_projects_for_prompt(self, projects: list) -> list:
        result = []
        for proj in projects:
            curr = ""
            if "desc" in proj:
                curr += format_list_as_string(proj["desc"], list_sep="\n  - ")
                curr += "\n"
                result.append(curr)
        return result

    def _format_skills_for_prompt(self, skills: list) -> list:
        result = []
        for cat in skills:
            curr = ""
            if cat.get("category", ""):
                curr += f"{cat['category']}: "
            if "skills" in cat:
                curr += "Proficient in " + ", ".join(cat["skills"])
                result.append(curr)
        return result

    def _format_skills_raw(self, skills_raw) -> list:
        skills = [
            {"category": "Technical", "skills": []},
            {"category": "Non-technical", "skills": []},
        ]
        # New flat format: {"technical": [...], "nonTechnical": [...]}
        if "technical" in skills_raw or "nonTechnical" in skills_raw:
            skills[0]["skills"] = [item["name"] for item in skills_raw.get("technical", [])]
            skills[1]["skills"] = [item["name"] for item in skills_raw.get("nonTechnical", [])]
        else:
            # Legacy format: multiple named categories; "practices" is non-technical
            for s in skills_raw:
                if s != "practices":
                    skills[0]["skills"] += [item["name"] for item in skills_raw[s]]
                else:
                    skills[1]["skills"] += [item["name"] for item in skills_raw[s]]
        return skills

    @staticmethod
    def _apply_highlight_correction(result, corrected_content: str):
        """Replace result.final_answer highlights with corrected bullets from reviewer."""
        lines = [line.strip() for line in corrected_content.splitlines() if line.strip()]
        from prompts import Resume_Section_Highlight
        result.final_answer = [
            Resume_Section_Highlight(highlight=line, relevance=5) for line in lines
        ]
        return result

    async def _rewrite_experience_async(self, exp_raw: dict) -> dict:
        exp = dict(exp_raw)
        experience_unedited = exp.get("summary") if exp.get("unedited", False) else ""
        if experience_unedited:
            writer_chain = build_section_highlighter_chain(self._get_llm())
            reviewer_chain = build_reviewer_chain(self._get_llm())
            inputs = {
                **format_prompt_inputs_as_strings(
                    prompt_inputs=["duties", "qualifications", "technical_skills", "non_technical_skills"],
                    **self.parsed_job,
                ),
                "section": experience_unedited,
                "revision_instruction": "",
            }
            result = await self._review_and_correct(
                writer_chain=writer_chain,
                reviewer_chain=reviewer_chain,
                inputs=inputs,
                extract_content=lambda r: "\n".join(h.highlight for h in r.final_answer) if r.final_answer else "",
                apply_correction=self._apply_highlight_correction,
                section_type="highlight",
            )
            highlights = sorted(result.final_answer, key=lambda d: d.relevance * -1)
            exp["highlights"] = [h.highlight for h in highlights]
        return exp

    async def _rewrite_project_async(self, proj_raw: dict) -> dict:
        proj = dict(proj_raw) if isinstance(proj_raw, dict) else proj_raw
        proj_unedited = proj.get("summary") if proj.get("unedited", False) else ""
        if proj_unedited:
            desc_combined = proj_unedited + " using " + proj.get("skills", "")
            writer_chain = build_section_highlighter_chain(self._get_llm())
            reviewer_chain = build_reviewer_chain(self._get_llm())
            inputs = {
                **format_prompt_inputs_as_strings(
                    prompt_inputs=["duties", "qualifications", "technical_skills", "non_technical_skills"],
                    **self.parsed_job,
                ),
                "section": desc_combined,
                "revision_instruction": "",
            }
            result = await self._review_and_correct(
                writer_chain=writer_chain,
                reviewer_chain=reviewer_chain,
                inputs=inputs,
                extract_content=lambda r: "\n".join(h.highlight for h in r.final_answer) if r.final_answer else "",
                apply_correction=self._apply_highlight_correction,
                section_type="highlight",
            )
            highlights = sorted(result.final_answer, key=lambda d: d.relevance * -1)
            proj["highlights"] = [h.highlight for h in highlights]
        return proj

    async def _extract_skills_async(self) -> list:
        chain = build_skills_matcher_chain(self._get_llm())
        experiences_formatted = self._format_experiences_for_prompt(
            self.resume_builder["experiences_raw"]
        )
        projects_formatted = self._format_projects_for_prompt(
            self.resume_builder["projects_raw"]
        )
        inputs = format_prompt_inputs_as_strings(
            prompt_inputs=["technical_skills", "non_technical_skills", "projects", "experiences"],
            **self.parsed_job,
            experiences=experiences_formatted,
            projects=projects_formatted,
        )
        result = await chain.ainvoke(inputs)
        extracted = result.final_answer
        skills = []
        if extracted.technical_skills:
            skills.append({"category": "Technical", "skills": extracted.technical_skills})
        if extracted.non_technical_skills:
            skills.append({"category": "Non-technical", "skills": extracted.non_technical_skills})
        return skills

    async def _review_and_correct(
        self,
        writer_chain,
        reviewer_chain,
        inputs: dict,
        extract_content,
        apply_correction,
        section_type: str,
    ):
        """
        Run writer → reviewer → apply correction.

        Writer is called once. If reviewer fails, corrected_content from the
        reviewer is applied directly via apply_correction rather than retrying
        the writer (which ignores revision instructions).

        Args:
            writer_chain: Async-invokable LangChain chain producing resume content.
            reviewer_chain: Async-invokable reviewer chain returning ReviewerOutput.
            inputs: Input dict for the writer chain.
            extract_content: Callable extracting the reviewable text from writer result.
            apply_correction: Callable(result, corrected_content) -> result that patches
                              the writer result in-place with the corrected text.
            section_type: "highlight" or "summary" — passed to the reviewer.

        Returns:
            The writer result, potentially patched with reviewer corrections.
        """
        result = await writer_chain.ainvoke(inputs)
        content = extract_content(result)

        review: ReviewerOutput = await reviewer_chain.ainvoke({
            "section_type": section_type,
            "content": content,
            "previous_feedback": "None",
        })

        if review.passed:
            return result

        if review.corrected_content:
            logger.info(
                "Reviewer corrected section_type='%s'. Issues: %s",
                section_type,
                review.issues,
            )
            return apply_correction(result, review.corrected_content)

        logger.warning(
            "Reviewer failed for section_type='%s' but provided no corrected_content. "
            "Using original writer result. Issues: %s",
            section_type,
            review.issues,
        )
        return result

    async def _run_parallel_steps(self):
        """Run experience rewriting, project rewriting, and skill extraction in parallel.
        Only processes sections listed in ai_config.sections (defaults to all four)."""
        logger.info("=========== Starting parallel steps ===========")
        start_time = time.time()
        active = self._active_sections()

        coros = {}
        if "experience" in active:
            coros["experiences"] = asyncio.gather(*[
                self._rewrite_experience_async(exp)
                for exp in self.resume_builder["experiences_raw"]
            ])
        if "projects" in active:
            coros["projects"] = asyncio.gather(*[
                self._rewrite_project_async(proj)
                for proj in self.resume_builder["projects_raw"]
            ])
        if "skills" in active:
            coros["skills"] = self._extract_skills_async()

        keys = list(coros.keys())
        results = await asyncio.gather(*coros.values())
        result_map = dict(zip(keys, results))

        # Merge results; fall back to raw data for skipped sections
        self.resume_builder["experiences"] = list(result_map.get("experiences", self.resume_builder["experiences_raw"]))
        self.resume_builder["projects"] = list(result_map.get("projects", self.resume_builder["projects_raw"]))
        self.resume_builder["skills"] = result_map.get("skills", [])
        logger.info(f"Parallel steps done in {time.time() - start_time:.2f}s")

    def update_experiences(self):
        logger.info("=========== Start updating experiences ===========")
        if not self.resume_builder:
            self.read_resume()
        results = asyncio.run(asyncio.gather(*[
            self._rewrite_experience_async(exp)
            for exp in self.resume_builder["experiences_raw"]
        ]))
        self.resume_builder["experiences"] = list(results)

    def update_projects(self):
        logger.info("=========== Start updating projects ===========")
        if not self.resume_builder:
            self.read_resume()
        results = asyncio.run(asyncio.gather(*[
            self._rewrite_project_async(proj)
            for proj in self.resume_builder["projects_raw"]
        ]))
        self.resume_builder["projects"] = list(results)

    def update_skills(self):
        logger.info("=========== Start extracting skills ===========")
        if not self.resume_builder:
            self.read_resume()
        self.resume_builder["skills"] = asyncio.run(self._extract_skills_async())

    def update_summary(self):
        logger.info("=========== Start updating summary ===========")
        if not self.resume_builder:
            self.read_resume()
        if "summary" not in self._active_sections():
            logger.info("Summary section skipped (not in ai_config.sections)")
            self.resume_builder["summary"] = self.resume_builder.get("summary_raw", "")
            return
        writer_chain = build_summary_writer_chain(self._get_llm())
        reviewer_chain = build_reviewer_chain(self._get_llm())
        inputs = {
            **format_prompt_inputs_as_strings(
                prompt_inputs=["company", "job_summary", "degrees", "projects", "experiences", "skills"],
                **self.parsed_job,
                degrees=self._get_degrees(),
                projects=self._format_projects_for_prompt(self.resume_builder["projects"]),
                experiences=self._format_experiences_for_prompt(self.resume_builder["experiences"]),
                skills=self._format_skills_for_prompt(self.resume_builder["skills"]),
            ),
            "revision_instruction": "",
        }

        def apply_summary_correction(result, corrected_content: str):
            result.final_answer = corrected_content.strip()
            return result

        result = asyncio.run(self._review_and_correct(
            writer_chain=writer_chain,
            reviewer_chain=reviewer_chain,
            inputs=inputs,
            extract_content=lambda r: r.final_answer,
            apply_correction=apply_summary_correction,
            section_type="summary",
        ))
        self.resume_builder["summary"] = result.final_answer

    def improve_final_resume(self):
        logger.info("=========== Start improving final resume ===========")
        chain = build_improver_chain(self._get_llm())
        inputs = format_prompt_inputs_as_strings(
            prompt_inputs=["duties", "qualifications", "technical_skills", "non_technical_skills",
                           "summary", "experiences", "projects", "education", "skills"],
            **self.parsed_job,
            education=utils.dict_to_yaml_string(dict(Education=self.resume_builder["education"])),
            projects=utils.dict_to_yaml_string(dict(Projects=self.resume_builder["projects"])),
            summary=self.resume_builder["summary"],
            experiences=utils.dict_to_yaml_string(dict(Experiences=self.resume_builder["experiences"])),
            skills=utils.dict_to_yaml_string(dict(Skills=self.resume_builder["skills"])),
        )
        try:
            chain.invoke(inputs)  # improvements are informational; result logged but not stored
        except Exception:
            logger.warning("improve_final_resume parsing failed — skipping (non-fatal)", exc_info=True)

    def finalize(self) -> dict:
        self.final_resume = dict(
            basics={**self.resume_builder["basic_info"], "summary": self.resume_builder["summary"]},
            education=self.resume_builder["education"],
            work=self.resume_builder["experiences"],
            projects=self.resume_builder["projects"],
            skills=self.resume_builder["skills"],
            activities={"achievements": self.resume_builder["achievements"]},
        )
        return self.final_resume

    def generate_resume_yaml(self):
        if not self.parsed_job or not self.resume_filename:
            self.read_and_parse_job()
        if not self.resume_builder:
            self.read_resume()
        self.final_resume = self.finalize()
        utils.write_yaml(self.final_resume, filename=f"{self.resume_filename}.yaml")

    def generate_json(self):
        resume_yaml = utils.read_yaml(filename=f"{self.resume_filename}.yaml")
        self.final_resume = yaml_to_json(resume_yaml)
        with open(f"{self.resume_filename}.json", "w", encoding="utf-8") as json_file:
            json.dump(self.final_resume, json_file)
        logger.info("Successfully generated json file.")

    def main(self):
        # Step 1 — parse job posting
        self.read_and_parse_job()
        # Step 2 — read raw resume
        self.read_resume()
        # Step 3 — parallel: rewrite experiences, projects, extract skills
        asyncio.run(self._run_parallel_steps())
        # Step 4 — write summary (depends on Step 3)
        self.update_summary()
        # Step 5 — improve final resume
        self.improve_final_resume()
        # Step 6 — finalize and persist
        self.generate_resume_yaml()
        self.generate_json()
