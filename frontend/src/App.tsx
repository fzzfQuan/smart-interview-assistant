import { useState, useCallback, useRef } from "react";
import { useAuth } from "./contexts/AuthContext";
import { uploadResumeStream } from "./api";
import type {
  Step,
  ResumeSchema,
  MatchReport,
  InterviewQuestions,
  ProgressEvent,
} from "./types";
import { STAGE_META, STAGE_ORDER } from "./types";
import LoginPage from "./components/LoginPage";
import RegisterPage from "./components/RegisterPage";
import StepUpload from "./components/StepUpload";
import StepProgress from "./components/StepProgress";
import StepResult from "./components/StepResult";
import StepError from "./components/StepError";

function AppContent() {
  const { user, token, logout } = useAuth();

  /* ── 未登录：展示登录/注册页 ── */
  const [authPage, setAuthPage] = useState<"login" | "register">("login");

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-50">
        {authPage === "login" ? (
          <LoginPage onSwitchToRegister={() => setAuthPage("register")} />
        ) : (
          <RegisterPage onSwitchToLogin={() => setAuthPage("login")} />
        )}
      </div>
    );
  }

  /* ── 已登录：三步流程 ── */
  return <MainFlow token={token} user={user} logout={logout} />;
}

function MainFlow({
  token,
  user,
  logout,
}: {
  token: string | null;
  user: NonNullable<ReturnType<typeof useAuth>["user"]>;
  logout: () => void;
}) {
  const [step, setStep] = useState<Step>("upload");
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [resume, setResume] = useState<ResumeSchema | null>(null);
  const [match, setMatch] = useState<MatchReport | null>(null);
  const [questions, setQuestions] = useState<InterviewQuestions | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const handleSubmit = useCallback(
    async (file: File, jobDescription: string) => {
      setError(null);
      setProgress(null);
      setResume(null);
      setMatch(null);
      setQuestions(null);
      setStep("processing");

      const abort = new AbortController();
      abortRef.current = abort;

      try {
        await uploadResumeStream(
          file,
          jobDescription,
          token,
          (p) => setProgress({ ...p }),
          (data: any) => {
            setResume(data.parsed_resume ?? null);
            setMatch(data.match_analysis ?? null);
            setQuestions(data.interview_questions ?? null);
          },
          (msg) => {
            setError(msg);
            setStep("error");
          },
          abort.signal
        );

        if (!abort.signal.aborted) {
          setStep("result");
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          setError(err.message || "分析请求失败");
          setStep("error");
        }
      }
    },
    [token]
  );

  const handleRetry = useCallback(() => {
    setStep("upload");
    setProgress(null);
    setResume(null);
    setMatch(null);
    setQuestions(null);
    setError(null);
  }, []);

  const handleReset = useCallback(() => {
    abortRef.current?.abort();
    setStep("upload");
    setProgress(null);
    setResume(null);
    setMatch(null);
    setQuestions(null);
    setError(null);
  }, []);

  const currentStage = progress?.stage ?? "start";

  const displayName = user.display_name || user.username;

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <h1 className="text-lg font-bold text-indigo-600 tracking-tight">
            智能面试助手
          </h1>
          <div className="flex items-center gap-4">
            {step !== "upload" && step !== "error" && (
              <button
                onClick={handleReset}
                className="text-sm text-gray-500 hover:text-indigo-600 transition-colors"
              >
                ← 重新开始
              </button>
            )}
            <span className="text-sm text-gray-400 hidden sm:inline">
              {displayName}
            </span>
            <button
              onClick={logout}
              className="text-sm text-gray-400 hover:text-red-500 transition-colors"
            >
              退出
            </button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8">
        {/* Step indicator */}
        <div className="flex items-center justify-center gap-1 mb-8">
          {[
            { key: "upload", label: "上传简历" },
            { key: "processing", label: "智能分析" },
            { key: "result", label: "分析结果" },
          ].map((s, i) => {
            const order = ["upload", "processing", "result", "error"];
            const cur = order.indexOf(step);
            const done = order.indexOf(s.key) < cur;
            const active = s.key === step;
            const failed = step === "error" && s.key === "processing";

            return (
              <div key={s.key} className="flex items-center">
                {i > 0 && (
                  <div
                    className={`w-8 h-px ${
                      done || active ? "bg-indigo-500" : failed ? "bg-red-300" : "bg-gray-200"
                    }`}
                  />
                )}
                <div className="flex items-center gap-1.5">
                  <span
                    className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${
                      failed
                        ? "bg-red-500 text-white"
                        : done
                          ? "bg-indigo-500 text-white"
                          : active
                            ? "bg-indigo-100 text-indigo-600 ring-2 ring-indigo-300"
                            : "bg-gray-100 text-gray-400"
                    }`}
                  >
                    {failed ? "✕" : done ? "✓" : i + 1}
                  </span>
                  <span
                    className={`text-sm hidden sm:inline ${
                      failed
                        ? "text-red-600 font-medium"
                        : active
                          ? "text-indigo-600 font-medium"
                          : done
                            ? "text-gray-600"
                            : "text-gray-400"
                    }`}
                  >
                    {failed ? "分析异常" : s.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Step content */}
        <div key={step} className="step-enter">
          {step === "upload" && (
            <StepUpload onSubmit={handleSubmit} initialError={error} />
          )}
          {step === "processing" && (
            <StepProgress
              progress={progress}
              stages={STAGE_ORDER}
              currentStage={currentStage}
              stageMeta={STAGE_META}
            />
          )}
          {step === "result" && (
            <StepResult
              resume={resume}
              match={match}
              questions={questions}
              onReset={handleReset}
            />
          )}
          {step === "error" && (
            <StepError
              message={error ?? "未知错误"}
              onRetry={handleRetry}
              onBack={handleReset}
            />
          )}
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return <AppContent />;
}
