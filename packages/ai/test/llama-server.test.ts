import { describe, expect, it } from "vitest";
import { getModel, getModels } from "../src/models.js";
import { complete } from "../src/stream.js";
import type { Context } from "../src/types.js";

async function isLlamaServerRunning(): Promise<boolean> {
	try {
		const resp = await fetch("http://127.0.0.1:8080/v1/models", { signal: AbortSignal.timeout(2000) });
		return resp.ok;
	} catch {
		return false;
	}
}

const llamaServerAvailable = await isLlamaServerRunning();

describe("llama-server provider", () => {
	it("should have llama-server provider registered with custom model", () => {
		const model = getModel("llama-server", "custom");
		expect(model).toBeDefined();
		expect(model.api).toBe("openai-completions");
		expect(model.provider).toBe("llama-server");
		expect(model.id).toBe("custom");
	});

	it("should have correct compat settings", () => {
		const model = getModel("llama-server", "custom");
		expect(model.compat?.supportsStore).toBe(false);
		expect(model.compat?.supportsDeveloperRole).toBe(false);
		expect(model.compat?.supportsReasoningEffort).toBe(false);
		expect(model.compat?.supportsStrictMode).toBe(false);
		expect(model.compat?.maxTokensField).toBe("max_tokens");
	});

	it("should list llama-server models", () => {
		const models = getModels("llama-server");
		expect(models.length).toBeGreaterThan(0);
		expect(models[0].provider).toBe("llama-server");
	});

	it("should have zero cost (local model)", () => {
		const model = getModel("llama-server", "custom");
		expect(model.cost.input).toBe(0);
		expect(model.cost.output).toBe(0);
	});

	describe.skipIf(!llamaServerAvailable)("live llama-server tests", () => {
		it("should complete a simple prompt", { timeout: 30000 }, async () => {
			const model = getModel("llama-server", "custom");
			const context: Context = {
				messages: [{ role: "user", content: "Say hello in one word.", timestamp: Date.now() }],
			};
			const response = await complete(model, context);
			expect(response).toBeDefined();
			expect(response.role).toBe("assistant");
			expect(response.content.length).toBeGreaterThan(0);
		});

		it("should handle tool calling", { timeout: 30000 }, async () => {
			const model = getModel("llama-server", "custom");
			const { Type } = await import("@sinclair/typebox");
			const context: Context = {
				messages: [{ role: "user", content: "What's the weather in Tokyo?", timestamp: Date.now() }],
				tools: [
					{
						name: "get_weather",
						description: "Get the current weather for a given city",
						parameters: Type.Object({
							city: Type.String({ description: "City name" }),
						}),
					},
				],
			};
			const response = await complete(model, context);
			expect(response).toBeDefined();
			expect(response.role).toBe("assistant");
			// Model should attempt tool call or respond with text
			const hasToolCall = response.content.some((b) => b.type === "toolCall");
			const hasText = response.content.some((b) => b.type === "text");
			expect(hasToolCall || hasText).toBe(true);
		});
	});
});
