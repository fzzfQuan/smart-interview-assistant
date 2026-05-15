interface Props {
  message: string;
  onRetry: () => void;
  onBack: () => void;
}

export default function StepError({ message, onRetry, onBack }: Props) {
  return (
    <div className="max-w-lg mx-auto">
      <div className="bg-white rounded-2xl shadow-sm border border-red-100 p-8 text-center">
        {/* Icon */}
        <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
          <span className="text-3xl">✕</span>
        </div>

        <h2 className="text-xl font-semibold text-gray-800 mb-2">
          分析流程异常
        </h2>

        <p className="text-sm text-gray-500 mb-2">分析过程中发生了错误：</p>

        {/* Error detail */}
        <div className="bg-red-50 border border-red-100 rounded-xl px-5 py-4 mb-6 text-left">
          <code className="text-sm text-red-700 leading-relaxed break-words">
            {message}
          </code>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={onBack}
            className="px-5 py-2.5 text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors"
          >
            ← 返回上传
          </button>
          <button
            onClick={onRetry}
            className="px-5 py-2.5 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition-colors active:scale-[0.98]"
          >
            重新分析
          </button>
        </div>
      </div>
    </div>
  );
}
