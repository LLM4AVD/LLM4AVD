# Detecting Authorization Vulnerabilities via LLM-Assisted Semantic Access Control Modeling

We propose LLM4AVD, an LLM-driven approach for detecting authorization vulnerabilities. LLM4AVD introduces a unified access control model that captures high-level business semantics and diverse authorization mechanisms across source-code-level, framework-level, and database-level authorizations. Leveraging LLMs, LLM4AVD automatically extracts comprehensive access control models of the target software and identifies potential vulnerabilities by detecting semantic inconsistencies in access control behaviors.

## Benchmark

We construct a new dataset, AuthVul, which contains 230 historical authorization vulnerabilities extracted from representative open-source Java Web applications and 19 vulnerabilities extracted from industrial applications. Due to confidentiality constraints, the detailed vulnerability information of these industrial applications cannot be publicly released. The open-source data is available [AuthVul](https://https://github.com/LLM4AVD/LLM4AVD/blob/main/benchmark.json)

## Results

The following table shows the vulnerability detection results of LLM4AVD on each open-source application:

![LLM4AVD Performance](https://github.com/LLM4AVD/LLM4AVD/blob/main/LLM4AVD%20Performance.jpg)

All detailed result files can be found in the [Results](https://github.com/LLM4AVD/LLM4AVD/tree/main/Results) directory.
