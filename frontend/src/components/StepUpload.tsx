import { useState, useRef, type FormEvent } from "react";

interface Props {
  onSubmit: (file: File, jobDescription: string) => void;
  initialError: string | null;
}

export default function StepUpload({ onSubmit, initialError }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [jobDesc, setJobDesc] = useState("");
  const [error, setError] = useState<string | null>(initialError);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!file) {
      setError("请选择简历文件");
      return;
    }

    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!ext || !["pdf", "docx", "txt"].includes(ext)) {
      setError("仅支持 PDF、DOCX、TXT 格式");
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      setError("文件大小不能超过 20MB");
      return;
    }

    onSubmit(file, jobDesc);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="max-w-xl mx-auto">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
        <h2 className="text-xl font-semibold text-gray-800 mb-2">上传简历</h2>
        <p className="text-sm text-gray-500 mb-6">
          上传候选人简历，AI 将自动解析并生成匹配分析和面试题
        </p>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* File drop zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all
              ${
                dragOver
                  ? "border-indigo-400 bg-indigo-50"
                  : file
                    ? "border-indigo-300 bg-indigo-50/50"
                    : "border-gray-200 hover:border-indigo-300 hover:bg-gray-50"
              }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />

            {file ? (
              <div className="flex flex-col items-center gap-2">
                <span className="text-3xl">
                  {file.name.endsWith(".pdf")
                    ? "📄"
                    : file.name.endsWith(".docx")
                      ? "📝"
                      : "📃"}
                </span>
                <span className="font-medium text-gray-700">{file.name}</span>
                <span className="text-xs text-gray-400">
                  {formatSize(file.size)}
                </span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                  }}
                  className="text-xs text-red-500 hover:text-red-700 mt-1"
                >
                  移除文件
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <span className="text-3xl text-gray-300">📁</span>
                <span className="font-medium text-gray-600">
                  点击或拖拽简历文件到此区域
                </span>
                <span className="text-xs text-gray-400">
                  支持 PDF、DOCX、TXT 格式，最大 20MB
                </span>
              </div>
            )}
          </div>

          {/* Job description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              目标职位描述
              <span className="text-gray-400 font-normal ml-1">（可选）</span>
            </label>
            <textarea
              value={jobDesc}
              onChange={(e) => setJobDesc(e.target.value)}
              rows={4}
              placeholder="粘贴职位描述，AI 将据此进行匹配度分析和针对性出题..."
              className="w-full rounded-lg border border-gray-200 px-3.5 py-2.5 text-sm
                placeholder-gray-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100
                outline-none resize-none transition-all"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-600">
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            className="w-full py-3 px-6 bg-indigo-600 hover:bg-indigo-700
              text-white font-medium rounded-xl transition-colors
              focus:outline-none focus:ring-2 focus:ring-indigo-300
              active:scale-[0.98]"
          >
            开始分析
          </button>
        </form>
      </div>
    </div>
  );
}
