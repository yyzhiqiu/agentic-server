import { useState } from "react";

export function useBoolean(initialValue = false) {
  const [value, setValue] = useState(initialValue);

  return {
    value,
    setTrue: () => setValue(true),
    setFalse: () => setValue(false),
    toggle: () => setValue((current) => !current),
  };
}
