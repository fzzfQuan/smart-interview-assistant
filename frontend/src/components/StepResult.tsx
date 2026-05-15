import type {
  ResumeSchema,
  MatchReport,
  InterviewQuestions,
} from "../types";
import ResumeCard from "./ResumeCard";
import MatchCard from "./MatchCard";
import QuestionsCard from "./QuestionsCard";

interface Props {
  resume: ResumeSchema | null;
  match: MatchReport | null;
  questions: InterviewQuestions | null;
  onReset: () => void;
}

export default function StepResult({
  resume,
  match,
  questions,
  onReset,
}: Props) {
  const sections = [];

  if (resume)
    sections.push({
      key: "resume",
      title: "简历信息",
      icon: "📋",
      component: <ResumeCard data={resume} />,
    });

  if (match)
    sections.push({
      key: "match",
      title: "匹配分析",
      icon: "📊",
      component: <MatchCard data={match} />,
    });

  if (questions)
    sections.push({
      key: "questions",
      title: "面试题",
      icon: "❓",
      component: <QuestionsCard data={questions} />,
    });

  if (sections.length === 0) {
    return (
      <div className="max-w-xl mx-auto text-center py-16">
        <span className="text-4xl">😕</span>
        <p className="mt-4 text-gray-500">暂无可用结果数据</p>
        <button
          onClick={onReset}
          className="mt-6 px-6 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          重新上传
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {sections.map((s) => (
        <div
          key={s.key}
          className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden"
        >
          <div className="px-6 py-4 border-b border-gray-50 flex items-center gap-2">
            <span className="text-lg">{s.icon}</span>
            <h2 className="font-semibold text-gray-800">{s.title}</h2>
          </div>
          <div className="px-6 py-5">{s.component}</div>
        </div>
      ))}

      <div className="text-center pb-8">
        <button
          onClick={onReset}
          className="px-6 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors active:scale-[0.98]"
        >
          重新分析
        </button>
      </div>
    </div>
  );
}
