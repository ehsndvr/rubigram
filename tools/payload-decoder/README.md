# Payload decoder

A static, offline page that decrypts recorded Rubika envelopes (`data_enc`)
with the same AES-CBC scheme as `rubigram.crypto.cipher`, for inspecting
traffic captured from the web client.  Open `index.html` in a browser; nothing
is sent anywhere.

Never paste a real `auth` into a page you do not control.
