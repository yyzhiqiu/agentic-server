import type {
  HumanInputField,
  HumanInputOption,
  PendingHumanInput,
} from "@/features/chat/types";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function readBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function readSnakeOrCamel(
  record: Record<string, unknown>,
  snakeKey: string,
  camelKey: string,
) {
  return record[snakeKey] ?? record[camelKey];
}

function mapHumanInputOptions(value: unknown): HumanInputOption[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((option) => {
      if (!isRecord(option)) {
        return null;
      }
      const label = readString(option.label);
      const optionValue = readString(option.value);
      if (!label || !optionValue) {
        return null;
      }
      return {
        label,
        value: optionValue,
      };
    })
    .filter((option): option is HumanInputOption => option !== null);
}

function mapHumanInputField(value: unknown): HumanInputField | null {
  if (!isRecord(value)) {
    return null;
  }

  const name = readString(value.name);
  const label = readString(value.label);
  const type = value.type;
  const required = readBoolean(value.required);
  if (
    !name ||
    !label ||
    (type !== "text" && type !== "select") ||
    required === null
  ) {
    return null;
  }

  return {
    name,
    label,
    type,
    required,
    placeholder: readString(value.placeholder),
    value: readString(value.value),
    allowCustom:
      readSnakeOrCamel(value, "allow_custom", "allowCustom") === true,
    customOptionLabel: readString(
      readSnakeOrCamel(value, "custom_option_label", "customOptionLabel"),
    ),
    customPlaceholder: readString(
      readSnakeOrCamel(value, "custom_placeholder", "customPlaceholder"),
    ),
    options: mapHumanInputOptions(value.options),
  };
}

export function mapPendingHumanInput(value: unknown): PendingHumanInput | null {
  if (!isRecord(value)) {
    return null;
  }

  const kind = value.kind;
  const title = readString(value.title);
  const message = readString(value.message);
  const submitLabel = readString(
    readSnakeOrCamel(value, "submit_label", "submitLabel"),
  );
  const rawFields = value.fields;
  const rawMissingFields = readSnakeOrCamel(
    value,
    "missing_fields",
    "missingFields",
  );

  if (
    kind !== "form" ||
    !title ||
    !message ||
    !submitLabel ||
    !Array.isArray(rawFields) ||
    !Array.isArray(rawMissingFields)
  ) {
    return null;
  }

  const fields = rawFields
    .map(mapHumanInputField)
    .filter((field): field is HumanInputField => field !== null);
  if (fields.length === 0) {
    return null;
  }

  return {
    kind: "form",
    title,
    message,
    fields,
    submitLabel,
    missingFields: rawMissingFields.filter(
      (field): field is string => typeof field === "string",
    ),
  };
}
