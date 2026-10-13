# Fixed input fixtures

[har_uci24.json](har_uci24.json) contains 24 real UCI HAR test inputs: four evenly spaced source rows per true class. It records source row IDs, feature selection, input scale, citation/license and dataset-file SHA-256. Selection does not depend on prediction correctness.

Gold is computed independently at runtime. Synthetic and full-dataset vectors are generated under ignored build/. These 24 rows are an integration fixture, not an overall accuracy estimate. See [model verification](../../docs/model-verification.md).
