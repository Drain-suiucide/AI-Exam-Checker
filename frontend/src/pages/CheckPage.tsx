import { useEffect, useMemo, useRef, useState } from "react";
import { Alert } from "../components/Alert";
import { Stepper } from "../components/Stepper";
import type { StepDefinition } from "../components/Stepper";
import { loadCheckApi } from "../api/loadCheckApi";
import type { CheckApi } from "../api/checkApi";
import { useSubmissionFlow } from "../features/check/useSubmissionFlow";
import { SetupStep } from "../features/check/SetupStep";
import { PreviewStep } from "../features/check/PreviewStep";
import { ProgressStep } from "../features/check/ProgressStep";
import { TranscriptionStep } from "../features/check/TranscriptionStep";
import { ResultStep } from "../features/check/ResultStep";

const STEPS: StepDefinition[] = [
  { key: "setup", label: "Ответ и конфигурация" },
  { key: "preview", label: "Предпросмотр" },
  { key: "transcription", label: "Текст ответа" },
  { key: "progress", label: "Обработка" },
  { key: "result", label: "Результат" },
];

const STEP_ORDER: Record<string, number> = {
  setup: 0,
  preview: 1,
  transcription: 2,
  progress: 3,
  result: 4,
};

export function CheckPage() {
  const [api, setApi] = useState<CheckApi | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    let cancelled = false;
    loadCheckApi()
      .then((value) => {
        if (!cancelled) setApi(value);
      })
      .catch(() => {
        if (!cancelled) setApiError("Не удалось инициализировать клиент API.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const flow = useSubmissionFlow(api);

  const currentStepIndex = useMemo(() => {
    if (flow.step === "progress") {
      return flow.submission?.status === "recognizing" ? 2 : 3;
    }
    return STEP_ORDER[flow.step] ?? 0;
  }, [flow.step, flow.submission?.status]);

  // Переводим фокус на заголовок при смене шага: пользователь клавиатуры
  // не должен искать новое содержимое.
  const previousStep = useRef(flow.step);
  useEffect(() => {
    if (previousStep.current !== flow.step) {
      previousStep.current = flow.step;
      headingRef.current?.focus();
    }
  }, [flow.step]);

  return (
    <div className="check-page">
      <header className="check-header">
        <p className="badge">Проверка ответа</p>
        <h1 className="page-title" id="check-title" tabIndex={-1} ref={headingRef}>
          Проверка развёрнутого ответа
        </h1>
        <p className="card-text">
          Исследовательский прототип: результат предварительный и не заменяет
          экспертную проверку.
        </p>
      </header>

      <Stepper steps={STEPS} current={currentStepIndex} completed={currentStepIndex} />

      {apiError && (
        <Alert tone="error" title="Ошибка инициализации" live="alert">
          <p>{apiError}</p>
        </Alert>
      )}

      {!api && !apiError && (
        <section className="card" aria-busy="true">
          <p className="card-text" role="status">
            Подключаемся к серверу проверки…
          </p>
        </section>
      )}

      {api && flow.step === "setup" && (
        <SetupStep
          configs={flow.configs}
          configsState={flow.configsState}
          configsError={flow.configsError}
          selectedConfig={flow.selectedConfig}
          onSelectConfig={flow.selectConfig}
          onReloadConfigs={flow.reloadConfigs}
          onSubmit={(input) => void flow.createSubmission(input)}
          busy={flow.busy === "create"}
          error={flow.error}
          onRetry={flow.retry}
          onDismissError={flow.dismissError}
        />
      )}

      {api && flow.submission && flow.step === "preview" && flow.token && (
        <PreviewStep
          api={api}
          submission={flow.submission}
          token={flow.token}
          busy={flow.busy === "recognize"}
          error={flow.error}
          onRecognize={() => void flow.recognize()}
          onRetry={flow.retry}
          onDismissError={flow.dismissError}
          onManualEntry={flow.startManualEntry}
          onStartOver={() => void flow.startOver()}
        />
      )}

      {api && flow.submission && flow.step === "progress" && (
        <ProgressStep
          submission={flow.submission}
          isSlow={flow.isSlow}
          pollError={flow.pollError}
          onRefresh={() => void flow.refreshSubmission()}
        />
      )}

      {api && flow.submission && flow.step === "transcription" && (
        <TranscriptionStep
          submission={flow.submission}
          transcription={flow.transcription}
          transcriptionState={flow.transcriptionState}
          transcriptionError={flow.transcriptionError}
          manualEntry={flow.manualEntry}
          busy={flow.busy}
          error={flow.error}
          onRetry={flow.retry}
          onDismissError={flow.dismissError}
          onReloadTranscription={() => {
            flow.loadTranscription();
          }}
          onSave={flow.saveTranscription}
          onEvaluate={(version) => void flow.evaluate(version)}
          onRecognize={() => void flow.recognize()}
          onStartOver={() => void flow.startOver()}
          onBackToResult={flow.showResult}
          hasResult={flow.submission.status === "evaluated"}
        />
      )}

      {api && flow.submission && flow.step === "result" && (
        <ResultStep
          submission={flow.submission}
          resultState={flow.resultState}
          reviewRequest={flow.reviewRequest}
          reviewError={flow.reviewError}
          busy={flow.busy === "review"}
          error={flow.error}
          onRetryResult={flow.reloadResult}
          onDismissError={flow.dismissError}
          onBackToText={flow.showTranscription}
          onStartOver={() => void flow.startOver()}
          onRequestReview={flow.requestReview}
        />
      )}
    </div>
  );
}
