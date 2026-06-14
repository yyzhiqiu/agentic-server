import type { FormEvent } from "react";
import { useEffect, useState } from "react";

import type { PendingHumanInput } from "@/features/chat/types";
import { Button } from "@/shared/components/ui/button";
import { Card } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";

const CUSTOM_OPTION_VALUE_PREFIX = "__custom__:";

type HumanInputFormProps = {
  pendingHumanInput: PendingHumanInput;
  disabled?: boolean;
  isSubmitting?: boolean;
  onCancel?: () => void;
  onSubmit: (input: Record<string, string>) => void;
};

function buildCustomOptionValue(fieldName: string) {
  return `${CUSTOM_OPTION_VALUE_PREFIX}${fieldName}`;
}

function isCustomOptionValue(fieldName: string, value: string | undefined) {
  return value === buildCustomOptionValue(fieldName);
}

function buildInitialValues(pendingHumanInput: PendingHumanInput) {
  const nextValues: Record<string, string> = {};
  const nextCustomValues: Record<string, string> = {};
  for (const field of pendingHumanInput.fields) {
    const fieldValue = typeof field.value === "string" ? field.value : "";
    if (
      field.type === "select" &&
      field.allowCustom &&
      fieldValue.length > 0 &&
      !field.options.some((option) => option.value === fieldValue)
    ) {
      nextValues[field.name] = buildCustomOptionValue(field.name);
      nextCustomValues[field.name] = fieldValue;
      continue;
    }
    if (fieldValue.length > 0) {
      nextValues[field.name] = fieldValue;
      continue;
    }
    if (field.type === "select" && field.options.length > 0) {
      nextValues[field.name] = field.options[0].value;
      continue;
    }
    nextValues[field.name] = "";
  }
  return {
    values: nextValues,
    customValues: nextCustomValues,
  };
}

export function HumanInputForm({
  pendingHumanInput,
  disabled = false,
  isSubmitting = false,
  onCancel,
  onSubmit,
}: HumanInputFormProps) {
  const initialState = buildInitialValues(pendingHumanInput);
  const [values, setValues] = useState<Record<string, string>>(initialState.values);
  const [customValues, setCustomValues] = useState<Record<string, string>>(
    initialState.customValues,
  );

  useEffect(() => {
    const nextState = buildInitialValues(pendingHumanInput);
    setValues(nextState.values);
    setCustomValues(nextState.customValues);
  }, [pendingHumanInput]);

  const canSubmit =
    !disabled &&
    !isSubmitting &&
    pendingHumanInput.fields.every((field) => {
      const selectedValue = values[field.name] ?? "";
      const effectiveValue =
        field.type === "select" && field.allowCustom && isCustomOptionValue(field.name, selectedValue)
          ? customValues[field.name] ?? ""
          : selectedValue;

      if (!field.required) {
        return true;
      }
      return effectiveValue.trim().length > 0;
    });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }

    const normalizedInput: Record<string, string> = {};
    for (const field of pendingHumanInput.fields) {
      const selectedValue = values[field.name] ?? "";
      if (
        field.type === "select" &&
        field.allowCustom &&
        isCustomOptionValue(field.name, selectedValue)
      ) {
        normalizedInput[field.name] = (customValues[field.name] ?? "").trim();
        continue;
      }
      normalizedInput[field.name] = selectedValue.trim();
    }
    onSubmit(normalizedInput);
  }

  return (
    <Card className="space-y-4 border-emerald-200 bg-emerald-50/50 dark:border-emerald-900/30 dark:bg-emerald-950/20">
      <div className="space-y-2">
        <p className="text-sm font-bold text-emerald-900 dark:text-emerald-400">
          {pendingHumanInput.title}
        </p>
        <p className="text-xs leading-5 text-emerald-800 dark:text-emerald-500">
          {pendingHumanInput.message}
        </p>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        {pendingHumanInput.fields.map((field) => (
          <label key={field.name} className="block space-y-2">
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-350">
              {field.label}
            </span>
            {field.type === "select" ? (
              <div className="space-y-3">
                <select
                  value={values[field.name] ?? ""}
                  disabled={disabled || isSubmitting}
                  onChange={(event) => {
                    const nextValue = event.target.value;
                    setValues((current) => ({
                      ...current,
                      [field.name]: nextValue,
                    }));
                    if (!isCustomOptionValue(field.name, nextValue)) {
                      setCustomValues((current) => ({
                        ...current,
                        [field.name]: "",
                      }));
                    }
                  }}
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition-all focus:border-brand-500 focus:ring-2 focus:ring-brand-500/10 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100 dark:focus:border-brand-400 dark:focus:ring-brand-400/10"
                >
                  {field.options.map((option) => (
                    <option key={option.value} value={option.value} className="dark:bg-slate-900">
                      {option.label}
                    </option>
                  ))}
                  {field.allowCustom ? (
                    <option value={buildCustomOptionValue(field.name)} className="dark:bg-slate-900">
                      {field.customOptionLabel ?? "其他"}
                    </option>
                  ) : null}
                </select>
                {field.allowCustom &&
                isCustomOptionValue(field.name, values[field.name]) ? (
                  <Input
                    value={customValues[field.name] ?? ""}
                    disabled={disabled || isSubmitting}
                    placeholder={
                      field.customPlaceholder ?? `请输入自定义${field.label}`
                    }
                    onChange={(event) => {
                      setCustomValues((current) => ({
                        ...current,
                        [field.name]: event.target.value,
                      }));
                    }}
                  />
                ) : null}
              </div>
            ) : (
              <Input
                value={values[field.name] ?? ""}
                disabled={disabled || isSubmitting}
                placeholder={field.placeholder ?? undefined}
                onChange={(event) => {
                  setValues((current) => ({
                    ...current,
                    [field.name]: event.target.value,
                  }));
                }}
              />
            )}
          </label>
        ))}

        <div className="flex flex-wrap justify-end gap-2">
          {onCancel ? (
            <Button
              type="button"
              variant="ghost"
              disabled={disabled || isSubmitting}
              onClick={onCancel}
              className="text-slate-650 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              取消本次规划
            </Button>
          ) : null}
          <Button type="submit" disabled={!canSubmit}>
            {isSubmitting ? "提交中..." : pendingHumanInput.submitLabel}
          </Button>
        </div>
      </form>
    </Card>
  );
}
