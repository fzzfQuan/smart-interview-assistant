import type { MatchReport } from "../types";

interface Props {
  data: MatchReport;
}

export default function MatchCard({ data }: Props) {
  const pct = Math.round(data.overall_score * 100);
  const scoreColor =
    pct >= 70
      ? "text-green-600 bg-green-50"
      : pct >= 40
        ? "text-yellow-600 bg-yellow-50"
        : "text-red-600 bg-red-50";

  return (
    <div className="space-y-5">
      {/* Overall score */}
      <div
        className={`text-center py-6 px-4 rounded-xl ${scoreColor.split(" ")[1]}`}
      >
        <div className={`text-5xl font-bold ${scoreColor.split(" ")[0]}`}>
          {pct}%
        </div>
        <div className="text-sm mt-1 text-gray-500">总体匹配度</div>
      </div>

      {data.summary && (
        <p className="text-sm text-gray-600 text-center leading-relaxed">
          {data.summary}
        </p>
      )}

      {data.experience_years != null && (
        <div className="text-center text-sm text-gray-500">
          经验年限：{data.experience_years} 年
        </div>
      )}

      {/* Category scores */}
      {data.category_scores.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            分类得分
          </h3>
          <div className="space-y-2.5">
            {data.category_scores.map((cat, i) => {
              const cpct = Math.round(cat.score * 100);
              const cColor =
                cat.score >= 0.7
                  ? "bg-green-500"
                  : cat.score >= 0.4
                    ? "bg-yellow-500"
                    : "bg-red-500";
              return (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-xs font-medium text-gray-600 w-16 text-right">
                    {cat.category}
                  </span>
                  <div className="flex-1 h-2.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${cColor}`}
                      style={{ width: `${cpct}%` }}
                    />
                  </div>
                  <span className="text-xs font-semibold text-gray-500 w-8 text-right tabular-nums">
                    {cpct}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Strengths & gaps */}
      {(data.strengths.length > 0 || data.gaps.length > 0) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {data.strengths.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-green-600 mb-2">
                优势
              </h4>
              <ul className="space-y-1">
                {data.strengths.map((s, i) => (
                  <li
                    key={i}
                    className="text-sm text-gray-600 flex items-start gap-2"
                  >
                    <span className="text-green-500 mt-0.5">•</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {data.gaps.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-red-600 mb-2">
                差距
              </h4>
              <ul className="space-y-1">
                {data.gaps.map((g, i) => (
                  <li
                    key={i}
                    className="text-sm text-gray-600 flex items-start gap-2"
                  >
                    <span className="text-red-500 mt-0.5">•</span>
                    {g}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
