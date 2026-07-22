#ifndef SECRETS_H
#define SECRETS_H

// Template for local credentials. Copy this file to secrets.h in the same
// directory and fill in the real values — secrets.h is gitignored and must
// never be committed.
//
//   cp epd7in3e/secrets.example.h epd7in3e/secrets.h
//
// config.h includes secrets.h automatically when it is present, and falls back
// to safe empty defaults when it is not.

// HTTP Basic Auth password — must match the server's APP_PASSWORD env var.
#define APP_PASSWORD ""

#endif // SECRETS_H
