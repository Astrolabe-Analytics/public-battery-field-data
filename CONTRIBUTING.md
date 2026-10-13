# Contributing

Thank you for helping. You can contribute in three ways: suggest a dataset, report an error, or help test a loader.

## What we include

The collection holds battery data recorded in real use: vehicles, grid and home storage, off-grid systems and similar. A dataset qualifies when the batteries ran in the field, the release has battery-level signals over time, anyone can download it without a login, and its license allows redistribution or a loader that reads the original files. [SCREENING.md](SCREENING.md) gives the full criteria and placement rules, and lists every dataset we have looked at with where it stands and why.

## Suggest a dataset

1. Check [SCREENING.md](SCREENING.md). If the dataset is already there, you can still add to it in an issue, for example a newer version or a license change.
2. Open an issue with the [dataset suggestion form](https://github.com/Astrolabe-Analytics/public-battery-field-data/issues/new?template=suggest-dataset.yml). A link and a few details are enough. Leave blank what you do not know.

## Report an error

Found a wrong number, a broken link, a download that fails or a loader that gives an error? Open an issue with the [error report form](https://github.com/Astrolabe-Analytics/public-battery-field-data/issues/new?template=report-error.yml). Tell us the release, what you ran, what you expected and what you saw. For a loader error, the output of `python -m fielddata.doctor <release>` helps.

## Help test a loader

When a new release is ready, we welcome people who will run its loader on their own download and tell us what fails or looks wrong. Say in an issue that you would like to help, and we will point you to it.

## What happens next

1. We reply to every issue.
2. For a suggestion, we screen the dataset against the criteria and list it in SCREENING.md with the reason for where it landed.
3. If it fits, we put it on deck and add it in a future release, with credit to you in SCREENING.md.
4. For an error, we check it against the release and the publisher's files, and fix it in the next release.

## Code

We are not set up to take pull requests yet. If you would like to contribute code, for example a loader for a new dataset, say so in an issue. If people want to, we will set this up for the next release. Until then, suggestions, error reports and testing are the most helpful.

## License

By contributing you agree that your contribution is shared under this repository's licenses: [LICENSE](LICENSE) (MIT) for code and [LICENSE-docs](LICENSE-docs) for text.
