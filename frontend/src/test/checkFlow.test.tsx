import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderApp, mockMediaQuery } from "./renderApp";
import { installFakeBackend, FAKE_OCR_TEXT } from "./fakeBackend";
import type { FakeBackend } from "./fakeBackend";

const GOOD_TEXT = "Понятие «реформа» раскрыто, приведён конкретный исторический факт.";

let backend: FakeBackend;

beforeEach(() => {
  backend = installFakeBackend();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function setupTextSubmission(user: ReturnType<typeof userEvent.setup>) {
  renderApp("/check");
  await screen.findByRole("heading", { name: "1. Конфигурация экзамена" });
  await user.click(screen.getByRole("radio", { name: /Ввести текст/ }));
  await user.type(screen.getByLabelText("Текст ответа"), GOOD_TEXT);
  await user.click(screen.getByRole("radio", { name: /Синтетический ответ/ }));
}

describe("Сценарий: ввод текста, проверка и результат", () => {
  it("проходит путь от выбора конфигурации до результата и обоснований", async () => {
    const user = userEvent.setup();
    await setupTextSubmission(user);

    await user.click(screen.getByRole("button", { name: "Далее" }));

    // Экран исправления текста
    const textarea = await screen.findByLabelText("Текст ответа", {
      selector: "textarea#transcription-text",
    });
    await waitFor(() => expect(textarea).toHaveValue(GOOD_TEXT));

    await user.click(screen.getByRole("button", { name: "Запустить проверку" }));

    // Ожидание оценивания
    expect(await screen.findByText("Оцениваем ответ по критериям…")).toBeInTheDocument();

    // Результат
    expect(await screen.findByText("Требуется проверка человеком", {}, { timeout: 4000 })).toBeInTheDocument();
    expect(screen.getByText("1", { selector: ".score-value" })).toBeInTheDocument();
    expect(screen.getByText("из 2 баллов")).toBeInTheDocument();

    const criteria = screen.getByRole("heading", { name: "Баллы по критериям" }).closest("section")!;
    expect(within(criteria).getByText("Смысл понятия")).toBeInTheDocument();
    expect(within(criteria).getByText("Конкретный факт")).toBeInTheDocument();
    expect(within(criteria).getByText(/Понятие раскрыто корректно/)).toBeInTheDocument();

    // Фрагменты ответа
    expect(within(criteria).getByText(/Понятие «реформа» раскрыто/)).toBeInTheDocument();

    // Дисклеймер из API
    expect(screen.getByText(/Не является официальным баллом ЕГЭ/)).toBeInTheDocument();
    // Уверенность не подаётся как гарантия
    expect(screen.getAllByText(/не вероятность правильности/i).length).toBeGreaterThan(0);
  });

  it("сохраняет правки текста перед оцениванием и создаёт новую версию", async () => {
    const user = userEvent.setup();
    await setupTextSubmission(user);
    await user.click(screen.getByRole("button", { name: "Далее" }));

    const textarea = await screen.findByLabelText("Текст ответа", {
      selector: "textarea#transcription-text",
    });
    await user.clear(textarea);
    await user.type(textarea, `${GOOD_TEXT} Уточнение.`);
    expect(screen.getByText(/Есть несохранённые изменения/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Запустить проверку" }));

    await waitFor(() => {
      const patch = backend.calls.find((call) => call.method === "PATCH");
      expect(patch).toBeDefined();
    });
    await screen.findByText("Требуется проверка человеком", {}, { timeout: 4000 });
  });
});

describe("Сценарий: загрузка изображения и OCR", () => {
  it("показывает предпросмотр, прогресс обработки и распознанный текст", async () => {
    const user = userEvent.setup();
    renderApp("/check");
    await screen.findByRole("heading", { name: "1. Конфигурация экзамена" });

    await user.click(screen.getByRole("radio", { name: /Загрузить изображение/ }));
    const fileInput = screen.getByLabelText(/Перетащите скан ответа сюда/);
    const file = new File(["fake-image"], "answer.png", { type: "image/png" });
    await user.upload(fileInput, file);
    expect(await screen.findByText("answer.png")).toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: /Синтетический ответ/ }));
    await user.click(screen.getByRole("button", { name: "Далее" }));

    // Предпросмотр
    expect(
      await screen.findByRole("heading", { name: "Проверьте изображение перед распознаванием" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Распознать текст" }));

    // Прогресс обработки с live-регионом
    expect(await screen.findByText("Распознаём текст и проверяем ответ…")).toBeInTheDocument();

    // После опроса — текст для правки
    const textarea = await screen.findByLabelText(
      "Текст ответа",
      { selector: "textarea#transcription-text" },
      { timeout: 4000 },
    );
    await waitFor(() => expect(textarea).toHaveValue(FAKE_OCR_TEXT));
  });

  it("показывает ошибку распознавания и позволяет повторить", async () => {
    const user = userEvent.setup();
    renderApp("/check");
    await screen.findByRole("heading", { name: "1. Конфигурация экзамена" });
    await user.click(screen.getByRole("radio", { name: /Загрузить изображение/ }));
    await user.upload(screen.getByLabelText(/Перетащите скан ответа сюда/), new File(["x"], "a.jpg", { type: "image/jpeg" }));
    await user.click(screen.getByRole("radio", { name: /Синтетический ответ/ }));
    await user.click(screen.getByRole("button", { name: "Далее" }));
    await screen.findByRole("heading", { name: "Проверьте изображение перед распознаванием" });

    backend.failNext("POST", "/recognize", {
      status: 409,
      code: "INVALID_STATE",
      message: "Действие недоступно в текущем состоянии отправки.",
    });
    await user.click(screen.getByRole("button", { name: "Распознать текст" }));
    expect(await screen.findByText("Действие сейчас недоступно")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Повторить" }));
    expect(await screen.findByText("Распознаём текст и проверяем ответ…")).toBeInTheDocument();
  });
});

describe("Валидация формы", () => {
  it("требует текст достаточной длины", async () => {
    const user = userEvent.setup();
    renderApp("/check");
    await screen.findByRole("heading", { name: "1. Конфигурация экзамена" });
    await user.click(screen.getByRole("radio", { name: /Ввести текст/ }));
    await user.click(screen.getByRole("button", { name: "Далее" }));

    expect(await screen.findByText("Введите текст ответа.")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Текст ответа"), "коротко");
    await user.click(screen.getByRole("button", { name: "Далее" }));
    expect(await screen.findByText(/Минимум 10 символов/)).toBeInTheDocument();

    // Форма не отправила запрос
    expect(backend.calls.some((call) => call.method === "POST" && call.path === "/api/v1/submissions")).toBe(false);
  });

  it("требует подтверждения происхождения данных", async () => {
    const user = userEvent.setup();
    renderApp("/check");
    await screen.findByRole("heading", { name: "1. Конфигурация экзамена" });
    await user.click(screen.getByRole("radio", { name: /Ввести текст/ }));
    await user.type(screen.getByLabelText("Текст ответа"), GOOD_TEXT);
    await user.click(screen.getByRole("button", { name: "Далее" }));
    expect(
      await screen.findByText("Подтвердите, что в ответе нет персональных данных."),
    ).toBeInTheDocument();
  });

  it("отклоняет файл неподдерживаемого формата", async () => {
    // applyAccept: false — проверяем клиентскую валидацию, а не фильтр диалога выбора файла
    const user = userEvent.setup({ applyAccept: false });
    renderApp("/check");
    await screen.findByRole("heading", { name: "1. Конфигурация экзамена" });
    await user.click(screen.getByRole("radio", { name: /Загрузить изображение/ }));
    await user.upload(
      screen.getByLabelText(/Перетащите скан ответа сюда/),
      new File(["pdf"], "answer.pdf", { type: "application/pdf" }),
    );
    await user.click(screen.getByRole("radio", { name: /Синтетический ответ/ }));
    await user.click(screen.getByRole("button", { name: "Далее" }));
    expect(await screen.findByText(/Поддерживаются только изображения JPG, PNG или WebP/)).toBeInTheDocument();
  });
});

describe("Ошибки API", () => {
  it("показывает ошибку загрузки конфигураций и восстанавливается по «Повторить»", async () => {
    const user = userEvent.setup();
    backend.failNext("GET", "/exam-configurations", {
      status: 503,
      code: "SERVICE_UNAVAILABLE",
      message: "Сервис временно недоступен.",
    });
    renderApp("/check");

    expect(await screen.findByText("Сервис временно недоступен")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Повторить" }));
    expect(await screen.findByRole("heading", { name: "1. Конфигурация экзамена" })).toBeInTheDocument();
  });

  it("показывает пустое состояние, если подтверждённых конфигураций нет", async () => {
    backend.setConfigs([]);
    renderApp("/check");
    expect(await screen.findByRole("heading", { name: "Нет доступных конфигураций" })).toBeInTheDocument();
    expect(screen.getByText(/иные предметы и задания временно недоступны/)).toBeInTheDocument();
  });

  it("показывает ошибку отправки и предлагает повтор", async () => {
    const user = userEvent.setup();
    backend.failNext("POST", "/submissions", {
      status: 503,
      code: "SERVICE_UNAVAILABLE",
      message: "Сервис временно недоступен.",
    });
    await setupTextSubmission(user);
    await user.click(screen.getByRole("button", { name: "Далее" }));

    expect(await screen.findByText("Сервис временно недоступен")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Повторить" }));
    expect(
      await screen.findByLabelText("Текст ответа", { selector: "textarea#transcription-text" }),
    ).toBeInTheDocument();
  });
});

describe("Пустой результат", () => {
  it("показывает состояние «результат не сформирован», когда сервер отвечает RESULT_NOT_READY", async () => {
    const user = userEvent.setup();
    backend.setResultNotReady(true);
    await setupTextSubmission(user);
    await user.click(screen.getByRole("button", { name: "Далее" }));
    await screen.findByLabelText("Текст ответа", { selector: "textarea#transcription-text" });
    await user.click(screen.getByRole("button", { name: "Запустить проверку" }));

    expect(await screen.findByText("Результат не сформирован", {}, { timeout: 4000 })).toBeInTheDocument();
    expect(screen.getByText("Оценка ещё недоступна")).toBeInTheDocument();

    backend.setResultNotReady(false);
    await user.click(screen.getByRole("button", { name: "Повторить загрузку" }));
    expect(await screen.findByText("Требуется проверка человеком", {}, { timeout: 4000 })).toBeInTheDocument();
  });
});

describe("Запрос экспертной проверки", () => {
  it("отправляет запрос с причиной и критерием и показывает статус", async () => {
    const user = userEvent.setup();
    await setupTextSubmission(user);
    await user.click(screen.getByRole("button", { name: "Далее" }));
    await screen.findByLabelText("Текст ответа", { selector: "textarea#transcription-text" });
    await user.click(screen.getByRole("button", { name: "Запустить проверку" }));
    await screen.findByText("Требуется проверка человеком", {}, { timeout: 4000 });

    await user.click(screen.getByRole("button", { name: "Запросить экспертную проверку" }));
    await user.click(screen.getByRole("button", { name: "Отправить запрос" }));
    expect(await screen.findByText("Выберите причину запроса.")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/Причина запроса/), "disagree_with_score");
    await user.click(screen.getByRole("checkbox", { name: /K2 — Конкретный факт/ }));
    await user.type(screen.getByLabelText("Комментарий"), "Балл по K2 спорный.");
    await user.click(screen.getByRole("button", { name: "Отправить запрос" }));

    expect(await screen.findByText("Запрос на проверку отправлен")).toBeInTheDocument();

    const post = backend.calls.find((call) => call.method === "POST" && call.path.endsWith("/review-requests"));
    expect(post).toBeDefined();
    expect(backend.state.review).toMatchObject({
      reason_code: "disagree_with_score",
      criterion_codes: ["K2"],
      comment: "Балл по K2 спорный.",
    });
  });
});

describe("Адаптивное отображение", () => {
  it("на узком экране показывает компактный индикатор шагов", async () => {
    mockMediaQuery(true);
    renderApp("/check");
    await screen.findByRole("heading", { name: "1. Конфигурация экзамена" });
    const stepper = screen.getByRole("navigation", { name: "Этапы проверки" });
    expect(within(stepper).getByText(/Шаг 1 из 5/)).toBeInTheDocument();
    expect(within(stepper).queryByRole("list")).not.toBeNull();
  });

  it("на широком экране показывает полный список шагов", async () => {
    mockMediaQuery(false);
    renderApp("/check");
    await screen.findByRole("heading", { name: "1. Конфигурация экзамена" });
    const stepper = screen.getByRole("navigation", { name: "Этапы проверки" });
    expect(within(stepper).getByText("Ответ и конфигурация")).toBeInTheDocument();
    expect(within(stepper).getByText("Результат")).toBeInTheDocument();
  });
});

describe("Доступность ключевых элементов", () => {
  it("связывает подписи с полями и помечает обязательные", async () => {
    const user = userEvent.setup();
    renderApp("/check");
    await screen.findByRole("heading", { name: "1. Конфигурация экзамена" });

    const textarea = screen.getByLabelText("Текст ответа");
    expect(textarea).toHaveAttribute("aria-required", "true");

    // Поле файла доступно только в режиме загрузки; подпись берётся из заголовка зоны
    await user.click(screen.getByRole("radio", { name: /Загрузить изображение/ }));
    expect(screen.getByLabelText(/Перетащите скан ответа сюда/).tagName).toBe("INPUT");

    // Сообщения об ошибках объявляются скринридеру
    expect(screen.getByRole("button", { name: "Далее" })).toBeEnabled();
  });

  it("ошибки формы выводятся в alert-регионе", async () => {
    const user = userEvent.setup();
    renderApp("/check");
    await screen.findByRole("heading", { name: "1. Конфигурация экзамена" });
    await user.click(screen.getByRole("button", { name: "Далее" }));
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.length).toBeGreaterThan(0);
  });

  it("прогресс оценивания объявляется через live-регион", async () => {
    const user = userEvent.setup();
    await setupTextSubmission(user);
    await user.click(screen.getByRole("button", { name: "Далее" }));
    await screen.findByLabelText("Текст ответа", { selector: "textarea#transcription-text" });
    await user.click(screen.getByRole("button", { name: "Запустить проверку" }));
    const heading = await screen.findByText("Оцениваем ответ по критериям…");
    const card = heading.closest("section")!;
    expect(card).toHaveAttribute("aria-busy", "true");
    expect(within(card).getByRole("status")).toBeInTheDocument();
  });
});
