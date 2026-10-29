import { useId, useRef, useState } from "react";
import type { DragEvent } from "react";

const ACCEPTED_MIME = ["image/jpeg", "image/png", "image/webp"];
const ACCEPTED_EXTENSIONS = ["jpg", "jpeg", "png", "webp"];

export interface FileValidationIssue {
  file: string;
  message: string;
}

/** Клиентская проверка файла: удобство, но не замена серверной (§3.3). */
export function validateFiles(
  files: File[],
  limits: { max_files: number; max_file_bytes: number; allowed_mime_types: string[] },
): FileValidationIssue[] {
  const issues: FileValidationIssue[] = [];
  if (files.length === 0) {
    issues.push({ file: "", message: "Выберите хотя бы один файл изображения." });
    return issues;
  }
  if (files.length > limits.max_files) {
    issues.push({
      file: "",
      message: `Можно загрузить не более ${limits.max_files} файлов.`,
    });
  }
  const allowed = limits.allowed_mime_types.length
    ? limits.allowed_mime_types
    : ACCEPTED_MIME;

  for (const file of files) {
    const extension = file.name.includes(".")
      ? file.name.slice(file.name.lastIndexOf(".") + 1).toLowerCase()
      : "";
    const typeOk = file.type ? allowed.includes(file.type) : false;
    const extensionOk = ACCEPTED_EXTENSIONS.includes(extension);
    if (!typeOk || !extensionOk) {
      issues.push({
        file: file.name,
        message:
          "Поддерживаются только изображения JPG, PNG или WebP. Проверьте формат файла.",
      });
    }
    if (file.size > limits.max_file_bytes) {
      issues.push({
        file: file.name,
        message: `Файл больше ${formatBytes(limits.max_file_bytes)}.`,
      });
    }
    if (file.size === 0) {
      issues.push({ file: file.name, message: "Файл пустой." });
    }
  }
  return issues;
}

export function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    const value = bytes / (1024 * 1024);
    return `${Number.isInteger(value) ? value : value.toFixed(1)} МБ`;
  }
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} КБ`;
  return `${bytes} Б`;
}

interface FileDropZoneProps {
  id?: string;
  files: File[];
  onChange: (files: File[]) => void;
  maxFiles: number;
  maxFileBytes: number;
  allowedMimeTypes: string[];
  disabled?: boolean;
}

/**
 * Зона загрузки: drag-and-drop + обычный выбор файла кнопкой/клавиатурой.
 * Поддерживает несколько страниц в порядке выбора.
 */
export function FileDropZone({
  id,
  files,
  onChange,
  maxFiles,
  maxFileBytes,
  allowedMimeTypes,
  disabled,
}: FileDropZoneProps) {
  const generatedId = useId();
  const inputId = id ?? `${generatedId}-file`;
  const hintId = `${inputId}-hint`;
  const [dragActive, setDragActive] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const accept = allowedMimeTypes.length ? allowedMimeTypes.join(",") : ACCEPTED_MIME.join(",");

  const addFiles = (incoming: File[]) => {
    const merged = [...files, ...incoming].slice(0, maxFiles);
    if (files.length + incoming.length > maxFiles) {
      setAnnouncement(
        `Добавлены первые ${maxFiles - files.length} файлов: всего допустимо ${maxFiles}.`,
      );
    } else {
      setAnnouncement(`Выбрано файлов: ${merged.length}.`);
    }
    onChange(merged);
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(false);
    if (disabled) return;
    const dropped = Array.from(event.dataTransfer?.files ?? []);
    if (dropped.length) addFiles(dropped);
  };

  const remove = (index: number) => {
    onChange(files.filter((_, i) => i !== index));
    setAnnouncement("Файл удалён из списка.");
  };

  return (
    <div className="dropzone-block">
      <div
        className={`dropzone${dragActive ? " dropzone-active" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        data-testid="dropzone"
      >
        <p className="dropzone-title" id={hintId}>
          Перетащите скан ответа сюда или выберите файл
        </p>
        <p className="dropzone-hint">
          Поддерживаются изображения JPG, PNG, WebP до {formatBytes(maxFileBytes)}.
          До {maxFiles} страниц в порядке следования.
        </p>
        <label className="button button-secondary" htmlFor={inputId}>
          Выбрать файл
        </label>
        <input
          id={inputId}
          ref={inputRef}
          className="visually-hidden"
          type="file"
          accept={accept}
          multiple={maxFiles > 1}
          disabled={disabled}
          aria-labelledby={hintId}
          onChange={(event) => {
            addFiles(Array.from(event.target.files ?? []));
            // Сброс позволяет выбрать тот же файл повторно после ошибки.
            event.target.value = "";
          }}
        />
      </div>

      <p className="visually-hidden" role="status" aria-live="polite">
        {announcement}
      </p>

      {files.length > 0 && (
        <ul className="file-list" aria-label="Выбранные файлы">
          {files.map((file, index) => (
            <li className="file-item" key={`${file.name}-${file.lastModified}-${index}`}>
              <span className="file-name">{file.name}</span>
              <span className="file-meta">
                {formatBytes(file.size)} · страница {index + 1}
              </span>
              <button
                type="button"
                className="button button-ghost button-small"
                onClick={() => remove(index)}
                aria-label={`Удалить файл ${file.name}`}
                disabled={disabled}
              >
                Удалить
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="dropzone-actions">
        <button
          type="button"
          className="button button-ghost button-small"
          onClick={() => inputRef.current?.click()}
          disabled={disabled || files.length >= maxFiles}
        >
          Добавить ещё файл
        </button>
      </div>
    </div>
  );
}
