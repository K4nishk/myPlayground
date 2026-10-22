# Local Model Gateway

One OpenAI-compatible front door to open-weight models on this Mac, with a
validator that proves every alias still answers correctly after each change.

## Language

### Gateway and models

**Gateway**:
The single front door every client calls; a request names an alias, never a backend.
_Avoid_: router, endpoint

**Alias**:
A stable name for a role at a tier (such as `local-reasoning`) that a client asks the gateway for; it maps to one backend model at a time and may be re-pointed.
_Avoid_: model endpoint, model name

**Role**:
The job an alias is for: reasoning, text or coding.
_Avoid_: model type, capability

**Tier**:
Where an alias's backend model runs: `local` is this Mac, `cluster` is Kubernetes on your own NVIDIA hardware, `frontier` is a vendor API.
_Avoid_: provider, location, "local" for the NVIDIA hardware

**Candidate**:
An alias pinned to one backend model for an experiment, and never re-pointed.
_Avoid_: experiment alias, test model

**Backend**:
A model server the gateway forwards requests to.
_Avoid_: provider, endpoint

**Backend model**:
The concrete model a backend serves for an alias.
_Avoid_: endpoint, alias

**Resident**:
A backend model loaded in memory, able to answer without first being loaded.
_Avoid_: running, active, hot

**Context window**:
The most tokens a resident model holds for one request, prompt and output together.
_Avoid_: max tokens, context size

**Output budget**:
The most tokens a case lets the model generate, thinking included.
_Avoid_: max tokens, limit

### Validation

**Case**:
One prompt sent to one alias, with the checks its answer must pass.
_Avoid_: test query, test

**Check**:
A single pass/fail rule applied to an answer.
_Avoid_: assertion, eval

**Run**:
One execution of the validator over the cases of every alias the gateway knows.
_Avoid_: test run, suite run

**Cold call**:
A call that forces its alias's backend model to load before answering.
_Avoid_: first call

**Warm call**:
A call answered by a backend model that was already resident.
_Avoid_: second call, cached call

**Misroute**:
A call to an alias answered by any backend model other than the one that alias maps to.
_Avoid_: wrong model, routing error

**Budget exhausted**:
A failed case where the model hit its output budget before giving a final answer.
_Avoid_: truncation, empty response

**Baseline**:
A passing run recorded as a dated story update so its numbers can be cited, valid only for the backend model each alias had at the time.
_Avoid_: benchmark, reference run
