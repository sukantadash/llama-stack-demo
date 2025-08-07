## Resources

Some of these APIs are associated with a set of **Resources**. Here is the mapping of APIs to resources:

- **Inference**, **Eval** and **Post Training** are associated with `Model` resources.
- **Safety** is associated with `Shield` resources.
- **Tool Runtime** is associated with `ToolGroup` resources.
- **DatasetIO** is associated with `Dataset` resources.
- **VectorIO** is associated with `VectorDB` resources.
- **Scoring** is associated with `ScoringFunction` resources.
- **Eval** is associated with `Model` and `Benchmark` resources.

Furthermore, we allow these resources to be **federated** across multiple providers. For example, you may have some Llama models served by Fireworks while others are served by AWS Bedrock. Regardless, they will all work seamlessly with the same uniform Inference API provided by Llama Stack.

```{admonition} Registering Resources
:class: tip

Given this architecture, it is necessary for the Stack to know which provider to use for a given resource. This means you need to explicitly _register_ resources (including models) before you can use them with the associated APIs.
```
