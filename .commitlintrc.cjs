module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [
      2,
      "always",
      [
        "build",
        "chore",
        "ci",
        "docs",
        "feat",
        "fix",
        "perf",
        "refactor",
        "revert",
        "style",
        "test",
      ],
    ],
    "scope-case": [2, "always", "kebab-case"],
    "header-max-length": [2, "always", 100],
    "subject-case": [0], // permette maiuscole iniziali in italiano
    "body-max-line-length": [1, "always", 120],
  },
};
