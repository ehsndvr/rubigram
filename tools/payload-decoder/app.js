const form = document.getElementById("decoder-form");
const keyModeInput = document.getElementById("key-mode");
const sessionKeyInput = document.getElementById("session-key");
const payloadInput = document.getElementById("payload-input");
const output = document.getElementById("decoded-output");
const fillSampleButton = document.getElementById("fill-sample");
const clearButton = document.getElementById("clear-form");
const copyButton = document.getElementById("copy-output");

function caesarDecode(value) {
  let result = "";

  for (const ch of value) {
    const code = ch.charCodeAt(0);

    if (ch >= "0" && ch <= "9") {
      result += String.fromCharCode(((code - 48 - 3 + 10) % 10) + 48);
    } else if (ch >= "A" && ch <= "Z") {
      result += String.fromCharCode(((code - 65 - 3 + 26) % 26) + 65);
    } else {
      const offset = code - 97;
      result += String.fromCharCode(((32 - offset + 26) % 26) + 97);
    }
  }

  return result;
}

function createSecretPassphrase(value) {
  const t = value.slice(0, 8);
  const i = value.slice(8, 16);
  const n = value.slice(16, 24) + t + value.slice(24, 32) + i;

  let result = "";
  for (const ch of n) {
    const code = ch.charCodeAt(0);

    if (ch >= "0" && ch <= "9") {
      result += String.fromCharCode(((code - 48 + 5) % 10) + 48);
    } else {
      result += String.fromCharCode(((code - 97 + 9) % 26) + 97);
    }
  }

  return result;
}

function parsePayload(rawValue) {
  const parsed = JSON.parse(rawValue);

  if (typeof parsed === "string") {
    return { data_enc: parsed };
  }

  if (!parsed || typeof parsed !== "object") {
    throw new Error("Payload باید JSON object یا string باشد.");
  }

  if (!parsed.data_enc || typeof parsed.data_enc !== "string") {
    throw new Error("فیلد data_enc داخل payload پیدا نشد.");
  }

  return parsed;
}

function resolvePayloadKey(payload) {
  if (payload && typeof payload.tmp_session === "string" && payload.tmp_session.trim()) {
    return {
      key: payload.tmp_session.trim(),
      source: "payload.tmp_session",
    };
  }

  if (payload && typeof payload.auth === "string" && payload.auth.trim()) {
    return {
      key: caesarDecode(payload.auth.trim()),
      source: "payload.auth",
    };
  }

  return null;
}

function base64ToBytes(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }

  return bytes;
}

async function decryptPayload(dataEnc, sessionKey) {
  const aesKey = createSecretPassphrase(sessionKey);
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(aesKey),
    { name: "AES-CBC" },
    false,
    ["decrypt"],
  );

  const plaintextBuffer = await crypto.subtle.decrypt(
    {
      name: "AES-CBC",
      iv: new Uint8Array(16),
    },
    cryptoKey,
    base64ToBytes(dataEnc),
  );

  const decoded = new TextDecoder().decode(plaintextBuffer);
  return JSON.parse(decoded);
}

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function resolveSessionKey(payload) {
  const payloadKey = resolvePayloadKey(payload);
  if (payloadKey) {
    return payloadKey;
  }

  const raw = sessionKeyInput.value.trim();
  if (!raw) {
    throw new Error("نه داخل payload کلیدی پیدا شد و نه auth دستی وارد شده است.");
  }

  if (keyModeInput.value === "encoded-auth") {
    return {
      key: caesarDecode(raw),
      source: "manual-auth-encoded",
    };
  }

  return {
    key: raw,
    source: "manual-auth",
  };
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    const payload = parsePayload(payloadInput.value.trim());
    const resolvedKey = resolveSessionKey(payload);
    const decrypted = await decryptPayload(payload.data_enc, resolvedKey.key);

    output.textContent = pretty({
      key_source: resolvedKey.source,
      resolved_auth: resolvedKey.key,
      decoded: decrypted,
    });
  } catch (error) {
    output.textContent = `Decode failed\n\n${error instanceof Error ? error.message : String(error)}`;
  }
});

fillSampleButton.addEventListener("click", () => {
  sessionKeyInput.value = "your-auth";
  payloadInput.value = pretty({
    auth: "ENCODED_AUTH_ON_WIRE",
    data_enc: "BASE64_ENCRYPTED_PAYLOAD",
  });
  output.textContent = "Sample loaded.";
});

clearButton.addEventListener("click", () => {
  sessionKeyInput.value = "";
  payloadInput.value = "";
  output.textContent = "منتظر payload...";
});

copyButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(output.textContent);
    copyButton.textContent = "Copied";
    window.setTimeout(() => {
      copyButton.textContent = "Copy";
    }, 1200);
  } catch (error) {
    output.textContent += `\n\nClipboard failed: ${error instanceof Error ? error.message : String(error)}`;
  }
});
