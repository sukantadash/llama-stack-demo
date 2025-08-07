## Distributions

While there is a lot of flexibility to mix-and-match providers, often users will work with a specific set of providers (hardware support, contractual obligations, etc.) We therefore need to provide a _convenient shorthand_ for such collections. We call this shorthand a **Llama Stack Distribution** or a **Distro**. One can think of it as specific pre-packaged versions of the Llama Stack. Here are some examples:

**Remotely Hosted Distro**: These are the simplest to consume from a user perspective. You can simply obtain the API key for these providers, point to a URL and have _all_ Llama Stack APIs working out of the box. Currently, [Fireworks](https://fireworks.ai/) and [Together](https://together.xyz/) provide such easy-to-consume Llama Stack distributions.

**Locally Hosted Distro**: You may want to run Llama Stack on your own hardware. Typically though, you still need to use Inference via an external service. You can use providers like HuggingFace TGI, Fireworks, Together, etc. for this purpose. Or you may have access to GPUs and can run a [vLLM](https://github.com/vllm-project/vllm) or [NVIDIA NIM](https://build.nvidia.com/nim?filters=nimType%3Anim_type_run_anywhere&q=llama) instance. If you "just" have a regular desktop machine, you can use [Ollama](https://ollama.com/) for inference. To provide convenient quick access to these options, we provide a number of such pre-configured locally-hosted Distros.

**On-device Distro**: To run Llama Stack directly on an edge device (mobile phone or a tablet), we provide Distros for [iOS](https://llama-stack.readthedocs.io/en/latest/distributions/ondevice_distro/ios_sdk.html) and [Android](https://llama-stack.readthedocs.io/en/latest/distributions/ondevice_distro/android_sdk.html)
