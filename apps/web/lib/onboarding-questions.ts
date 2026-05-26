/**
 * Hardcoded onboarding questions.
 *
 * Source of truth lives here on the frontend so onboarding works regardless
 * of any backend question-bank seed state. The backend just accepts the
 * resulting profile patch via POST /api/v1/profile/upsert.
 */

import type { ExamTarget } from "./api/types";

export type ProfileField =
  | "weak_subject"
  | "strong_subject"
  | "learning_style"
  | "mock_score_range"
  | "main_problem"
  | "mistake_pattern"
  | "emotional_state"
  | "revision_habit"
  | "study_hours_per_day";

export type AnswerType = "single_choice" | "short_text" | "number";

export interface OnboardingQuestion {
  id: string;
  field: ProfileField;
  text: string;
  type: AnswerType;
  options?: string[];
  exams: ExamTarget[];
}

const JEE_EXAMS: ExamTarget[] = ["jee_main", "jee_advanced", "jee_main_advanced"];
const NEET_EXAMS: ExamTarget[] = ["neet"];

export const ONBOARDING_QUESTIONS: OnboardingQuestion[] = [
  // ── JEE ───────────────────────────────────────────────────────────────
  {
    id: "JEE_MOCK_SCORE",
    field: "mock_score_range",
    text: "What is your current average score range in JEE mock tests?",
    type: "single_choice",
    options: ["Below 50", "50-100", "100-150", "150-200", "200-250", "250+"],
    exams: JEE_EXAMS,
  },
  {
    id: "JEE_STRONG_SUBJECT",
    field: "strong_subject",
    text: "Which subject are you most confident in right now?",
    type: "single_choice",
    options: ["physics", "chemistry", "mathematics"],
    exams: JEE_EXAMS,
  },
  {
    id: "JEE_WEAK_SUBJECT",
    field: "weak_subject",
    text: "Which subject consistently lowers your overall score?",
    type: "single_choice",
    options: ["physics", "chemistry", "mathematics"],
    exams: JEE_EXAMS,
  },
  {
    id: "JEE_WEAK_TOPICS",
    field: "main_problem",
    text: "Which chapters or topics do you consistently struggle with?",
    type: "short_text",
    exams: JEE_EXAMS,
  },
  {
    id: "JEE_MISTAKE_REASON",
    field: "mistake_pattern",
    text: "What is usually the biggest reason behind your low mock scores?",
    type: "single_choice",
    options: [
      "lack of concepts",
      "silly mistakes",
      "panic",
      "time management",
      "negative marking",
    ],
    exams: JEE_EXAMS,
  },
  {
    id: "JEE_FOCUS_HOURS",
    field: "study_hours_per_day",
    text: "How many hours do you actually study with full focus daily?",
    type: "number",
    exams: JEE_EXAMS,
  },
  {
    id: "JEE_REVISION_HABIT",
    field: "revision_habit",
    text: "How regularly do you revise completed chapters?",
    type: "single_choice",
    options: ["daily", "every few days", "before tests only", "rarely"],
    exams: JEE_EXAMS,
  },
  {
    id: "JEE_EMOTIONAL_STATE",
    field: "emotional_state",
    text: "What worries you the most currently in your JEE preparation?",
    type: "single_choice",
    options: [
      "low mock scores",
      "backlog",
      "parent pressure",
      "competition",
      "consistency",
      "fear of failure",
    ],
    exams: JEE_EXAMS,
  },
  {
    id: "JEE_LEARNING_STYLE",
    field: "learning_style",
    text: "What kind of explanation helps you understand fastest?",
    type: "single_choice",
    options: ["basic_explanation", "examples", "tricks", "step_by_step", "visual"],
    exams: JEE_EXAMS,
  },

  // ── NEET ──────────────────────────────────────────────────────────────
  {
    id: "NEET_MOCK_SCORE",
    field: "mock_score_range",
    text: "What is your current average NEET mock score range?",
    type: "single_choice",
    options: ["Below 300", "300-450", "450-550", "550-620", "620-680", "680+"],
    exams: NEET_EXAMS,
  },
  {
    id: "NEET_STRONG_SUBJECT",
    field: "strong_subject",
    text: "Which subject do you feel most confident in right now?",
    type: "single_choice",
    options: ["physics", "chemistry", "biology"],
    exams: NEET_EXAMS,
  },
  {
    id: "NEET_WEAK_SUBJECT",
    field: "weak_subject",
    text: "Which subject consistently pulls your overall score down?",
    type: "single_choice",
    options: ["physics", "chemistry", "biology"],
    exams: NEET_EXAMS,
  },
  {
    id: "NEET_WEAK_TOPICS",
    field: "main_problem",
    text: "Which chapters or topics are still weak or incomplete?",
    type: "short_text",
    exams: NEET_EXAMS,
  },
  {
    id: "NEET_MISTAKE_REASON",
    field: "mistake_pattern",
    text: "What is usually the biggest reason behind your low mock scores?",
    type: "single_choice",
    options: [
      "lack of concepts",
      "silly mistakes",
      "panic",
      "time management",
      "negative marking",
    ],
    exams: NEET_EXAMS,
  },
  {
    id: "NEET_FOCUS_HOURS",
    field: "study_hours_per_day",
    text: "How many hours of focused study do you actually complete daily?",
    type: "number",
    exams: NEET_EXAMS,
  },
  {
    id: "NEET_REVISION_HABIT",
    field: "revision_habit",
    text: "Do you revise regularly, or only before tests and exams?",
    type: "single_choice",
    options: ["daily", "every few days", "before tests only", "rarely"],
    exams: NEET_EXAMS,
  },
  {
    id: "NEET_EMOTIONAL_STATE",
    field: "emotional_state",
    text: "What is your biggest fear regarding the NEET exam?",
    type: "single_choice",
    options: [
      "low mock scores",
      "backlog",
      "parent pressure",
      "competition",
      "consistency",
      "fear of failure",
    ],
    exams: NEET_EXAMS,
  },
  {
    id: "NEET_LEARNING_STYLE",
    field: "learning_style",
    text: "What kind of explanation helps you understand fastest?",
    type: "single_choice",
    options: ["basic_explanation", "examples", "tricks", "step_by_step", "visual"],
    exams: NEET_EXAMS,
  },
];

export function questionsForExam(exam: ExamTarget): OnboardingQuestion[] {
  return ONBOARDING_QUESTIONS.filter((q) => q.exams.includes(exam));
}
