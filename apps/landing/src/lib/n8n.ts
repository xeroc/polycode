export async function addToWaitlist(args: Record<string, string>) {
  const n8nWebhookUrl = import.meta.env.VITE_N8N_WEBHOOK_URL;

  if (!n8nWebhookUrl) {
    throw new Error(
      "N8N webhook URL not configured. Please set VITE_N8N_WEBHOOK_URL environment variable.",
    );
  }

  try {
    const response = await fetch(n8nWebhookUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ...args,
        timestamp: new Date().toISOString(),
      }),
    });

    if (!response.ok) {
      throw new Error(`N8N webhook failed: ${response.statusText}`);
    }

    await response.json();
  } catch (error) {
    console.error("Failed to add to waitlist:", error);
    throw error;
  }
}
