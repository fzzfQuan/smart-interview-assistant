import type { ProgressEvent, StageMeta } from "../types";

interface Props {
  progress: ProgressEvent | null;
  stages: readonly string[];
  currentStage: string;
  stageMeta: Record<string, StageMeta>;
}

const STAGE_ICONS: Record<string, string> = {
  start: "🚀",
  load_pinned: "📌",
  extract: "📝",
  parse: "🔍",
  analyze: "📊",
  generate: "💡",
  save: "💾",
  done: "✅",
};

export default function StepProgress({
  progress,
  stages,
  currentStage,
  stageMeta,
}: Props) {
  const pct = progress?.percentage ?? 0;
  const message = progress?.message ?? "正在准备...";

  const currentIdx = stages.indexOf(currentStage);
  const activeIdx = currentIdx >= 0 ? currentIdx : 0;

  return (
    <div className="max-w-xl mx-auto">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
        <h2 className="text-xl font-semibold text-gray-800 mb-2">
          智能分析中
        </h2>
        <p className="text-sm text-gray-500 mb-8">
          AI 正在处理您的简历，请稍候...
        </p>

        {/* Progress bar */}
        <div className="mb-6">
          <div className="flex justify-between text-sm mb-2">
            <span className="font-medium text-indigo-600">{message}</span>
            <span className="text-gray-400 tabular-nums">{pct}%</span>
          </div>
          <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Stage list */}
        <div className="space-y-1">
          {stages.map((stage, idx) => {
            const meta = stageMeta[stage];
            const isActive = idx === activeIdx;
            const isDone = idx < activeIdx;
            const isPending = idx > activeIdx;

            return (
              <div
                key={stage}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm transition-all
                  ${isActive ? "bg-indigo-50 text-indigo-700 font-medium" : ""}
                  ${isDone ? "text-gray-500" : ""}
                  ${isPending ? "text-gray-300" : ""}
                `}
              >
                {/* Icon */}
                <span
                  className={`text-lg ${isPending ? "opacity-40" : ""}`}
                >
                  {isDone
                    ? "✓"
                    : isActive
                      ? "●"
                      : STAGE_ICONS[stage] ?? "○"}
                </span>

                {/* Label */}
                <span className="flex-1">{meta?.label ?? stage}</span>

                {/* Status */}
                {isDone && (
                  <span className="text-xs text-green-500">已完成</span>
                )}
                {isActive && (
                  <span className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-pulse" />
                    <span className="text-xs text-indigo-500">进行中</span>
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
