export async function readTextStream(
  response: Response,
  onChunk: (chunk: string) => void,
) {
  const reader = response.body?.getReader();

  if (!reader) {
    return;
  }

  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();

    if (done) {
      break;
    }

    onChunk(decoder.decode(value, { stream: true }));
  }
}

type SseEnvelope = {
  event: string;
  data: string;
};

function parseSseChunk(chunk: string): SseEnvelope | null {
  const lines = chunk.split("\n");
  let event = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
      continue;
    }

    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  return {
    event,
    data: dataLines.join("\n"),
  };
}

export async function readSseStream(
  response: Response,
  onEvent: (event: string, data: string) => void,
) {
  const reader = response.body?.getReader();

  if (!reader) {
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    while (buffer.includes("\n\n")) {
      const separatorIndex = buffer.indexOf("\n\n");
      const chunk = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);

      const envelope = parseSseChunk(chunk);
      if (envelope) {
        onEvent(envelope.event, envelope.data);
      }
    }
  }

  if (buffer.trim().length > 0) {
    const envelope = parseSseChunk(buffer);
    if (envelope) {
      onEvent(envelope.event, envelope.data);
    }
  }
}
