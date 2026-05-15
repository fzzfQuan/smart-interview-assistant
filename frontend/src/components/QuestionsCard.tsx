import { useState } from "react";
import type { InterviewQuestions, Question, QuestionType } from "../types";

interface Props {
  data: InterviewQuestions;
}

const GROUPS: {
  key: QuestionType;
  label: string;
  icon: string;
}[] = [
  { key: "technical", label: "技术题", icon: "💻" },
  { key: "behavioral", label: "行为题", icon: "🤝" },
  { key: "project_deep_dive", label: "项目深挖题", icon: "🔍" },
];

function DifficultyBadge({ difficulty }: { difficulty: string }) {
  const map: Record<string, { label: string; style: string }> = {
    basic: {
      label: "基础",
      style: "bg-green-50 text-green-600",
    },
    intermediate: {
      label: "进阶",
      style: "bg-yellow-50 text-yellow-600",
    },
    advanced: {
      label: "深入",
      style: "bg-red-50 text-red-600",
    },
  };
  const m = map[difficulty] ?? {
    label: difficulty,
    style: "bg-gray-50 text-gray-500",
  };
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${m.style}`}
    >
      {m.label}
    </span>
  );
}

function QuestionItem({ q, index }: { q: Question; index: number }) {
  const [showRationale, setShowRationale] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);

  return (
    <div className="border-l-4 border-indigo-400 bg-gray-50 rounded-r-lg p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="text-sm font-medium text-gray-800">
          {index}. {q.content}
        </div>
        <DifficultyBadge difficulty={q.difficulty} />
      </div>

      <div className="flex gap-4 mt-2">
        {q.rationale && (
          <button
            onClick={() => setShowRationale(!showRationale)}
            className="text-xs text-indigo-500 hover:text-indigo-700 transition-colors"
          >
            {showRationale ? "收起理由" : "📖 出题理由"}
          </button>
        )}
        {q.reference_answer && (
          <button
            onClick={() => setShowAnswer(!showAnswer)}
            className="text-xs text-indigo-500 hover:text-indigo-700 transition-colors"
          >
            {showAnswer ? "收起答案" : "✅ 参考答案"}
          </button>
        )}
      </div>

      {showRationale && q.rationale && (
        <div className="mt-3 text-xs text-gray-600 bg-white rounded-lg p-3 border border-gray-100">
          {q.rationale}
        </div>
      )}
      {showAnswer && q.reference_answer && (
        <div className="mt-3 text-xs text-gray-600 bg-white rounded-lg p-3 border border-dashed border-gray-200">
          {q.reference_answer}
        </div>
      )}
    </div>
  );
}

export default function QuestionsCard({ data }: Props) {
  const hasAny = GROUPS.some((g) => (data[g.key]?.length ?? 0) > 0);

  if (!hasAny) {
    return (
      <p className="text-sm text-gray-400 text-center py-4">暂无面试题数据</p>
    );
  }

  return (
    <div className="space-y-6">
      {GROUPS.map((group) => {
        const items = data[group.key];
        if (!items || items.length === 0) return null;

        return (
          <div key={group.key}>
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
              <span>{group.icon}</span>
              <span>{group.label}</span>
              <span className="text-xs text-gray-400 font-normal">
                （{items.length} 题）
              </span>
            </h3>
            <div className="space-y-2">
              {items.map((q, i) => (
                <QuestionItem key={q.id} q={q} index={i + 1} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
