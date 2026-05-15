/* ── 枚举 ── */

export type SkillCategory =
  | "language"
  | "framework"
  | "tool"
  | "soft"
  | "domain";

export type QuestionDifficulty = "basic" | "intermediate" | "advanced";

export type QuestionType = "technical" | "behavioral" | "project_deep_dive";

/* ── 简历 ── */

export interface Skill {
  name: string;
  category: SkillCategory;
  proficiency: number | null;
}

export interface Experience {
  company: string;
  title: string;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
  achievements: string[];
  skills_used: string[];
}

export interface Education {
  institution: string;
  degree: string;
  field: string | null;
  start_date: string | null;
  end_date: string | null;
}

export interface Project {
  name: string;
  description: string;
  technologies: string[];
  highlights: string[];
}

export interface PersonalInfo {
  name: string | null;
  email: string | null;
  phone: string | null;
  title: string | null;
  summary: string | null;
}

export interface ResumeSchema {
  personal_info: PersonalInfo;
  skills: Skill[];
  experiences: Experience[];
  education: Education[];
  projects: Project[];
}

/* ── 匹配分析 ── */

export interface CategoryScore {
  category: SkillCategory;
  score: number;
  matched: string[];
  missing: string[];
}

export interface MatchReport {
  overall_score: number;
  category_scores: CategoryScore[];
  strengths: string[];
  gaps: string[];
  experience_years: number | null;
  summary: string | null;
}

/* ── 面试题 ── */

export interface Question {
  id: string;
  type: QuestionType;
  difficulty: QuestionDifficulty;
  content: string;
  rationale: string | null;
  reference_answer: string | null;
}

export interface InterviewQuestions {
  technical: Question[];
  behavioral: Question[];
  project_deep_dive: Question[];
}

/* ── SSE 事件 ── */

export interface ProgressEvent {
  stage: string;
  percentage: number;
  message: string;
}

export interface ResultEvent {
  session_id: string;
  parsed_resume: ResumeSchema | null;
  match_analysis: MatchReport | null;
  interview_questions: InterviewQuestions | null;
}

export interface MetaEvent {
  session_id: string;
}

export interface ErrorEvent {
  message: string;
}

/* ── 步骤状态 ── */

export type Step = "upload" | "processing" | "result" | "error";

export interface StageMeta {
  stage: string;
  label: string;
  percentage: number;
}

export const STAGE_META: Record<string, StageMeta> = {
  start: { stage: "start", label: "启动分析", percentage: 0 },
  load_pinned: { stage: "load_pinned", label: "加载上下文", percentage: 10 },
  extract: { stage: "extract", label: "文本预处理", percentage: 15 },
  parse: { stage: "parse", label: "简历解析", percentage: 40 },
  analyze: { stage: "analyze", label: "匹配分析", percentage: 65 },
  generate: { stage: "generate", label: "生成面试题", percentage: 85 },
  save: { stage: "save", label: "保存结果", percentage: 95 },
  done: { stage: "done", label: "完成", percentage: 100 },
};

export const STAGE_ORDER = [
  "start",
  "load_pinned",
  "extract",
  "parse",
  "analyze",
  "generate",
  "save",
  "done",
] as const;
