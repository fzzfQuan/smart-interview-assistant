import type { ResumeSchema } from "../types";

interface Props {
  data: ResumeSchema;
}

export default function ResumeCard({ data }: Props) {
  const p = data.personal_info;

  return (
    <div className="space-y-5">
      {/* Personal info */}
      <div className="grid grid-cols-2 gap-3">
        {p.name && (
          <InfoItem label="姓名" value={p.name} />
        )}
        {p.email && (
          <InfoItem label="邮箱" value={p.email} />
        )}
        {p.phone && (
          <InfoItem label="电话" value={p.phone} />
        )}
        {p.title && (
          <InfoItem label="职位" value={p.title} />
        )}
      </div>
      {p.summary && (
        <p className="text-sm text-gray-600 leading-relaxed">{p.summary}</p>
      )}

      {/* Skills */}
      {data.skills.length > 0 && (
        <Section title="技能">
          <div className="flex flex-wrap gap-2">
            {data.skills.map((s, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-600"
              >
                {s.name}
                {s.proficiency != null && (
                  <span className="text-indigo-400">
                    {Math.round(s.proficiency * 100)}%
                  </span>
                )}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* Experience */}
      {data.experiences.length > 0 && (
        <Section title="工作经历">
          <div className="space-y-3">
            {data.experiences.map((exp, i) => (
              <div
                key={i}
                className="bg-gray-50 rounded-lg p-4 border border-gray-100"
              >
                <div className="font-medium text-gray-800">
                  {exp.title}
                  <span className="text-gray-500 font-normal">
                    {" "}
                    @ {exp.company}
                  </span>
                </div>
                {(exp.start_date || exp.end_date) && (
                  <div className="text-xs text-gray-400 mt-0.5">
                    {exp.start_date ?? ""} ~ {exp.end_date ?? "至今"}
                  </div>
                )}
                {exp.description && (
                  <p className="text-sm text-gray-600 mt-2">
                    {exp.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Education */}
      {data.education.length > 0 && (
        <Section title="教育背景">
          <div className="space-y-2">
            {data.education.map((edu, i) => (
              <div key={i} className="text-sm text-gray-700">
                <span className="font-medium">{edu.degree}</span>
                <span className="text-gray-400"> — </span>
                <span>{edu.institution}</span>
                {edu.field && (
                  <span className="text-gray-500"> ({edu.field})</span>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Projects */}
      {data.projects.length > 0 && (
        <Section title="项目经历">
          <div className="space-y-3">
            {data.projects.map((proj, i) => (
              <div
                key={i}
                className="bg-gray-50 rounded-lg p-4 border border-gray-100"
              >
                <div className="font-medium text-gray-800">{proj.name}</div>
                <p className="text-sm text-gray-600 mt-1">
                  {proj.description}
                </p>
                {proj.technologies.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {proj.technologies.map((t, j) => (
                      <span
                        key={j}
                        className="px-2 py-0.5 rounded text-xs bg-white text-gray-500 border border-gray-200"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="text-xs text-gray-400 uppercase tracking-wider">
        {label}
      </div>
      <div className="text-sm font-medium text-gray-800 mt-0.5">{value}</div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2.5">{title}</h3>
      {children}
    </div>
  );
}
