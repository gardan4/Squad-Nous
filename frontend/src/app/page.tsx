import { ChatWindow } from "@/components/ChatWindow";

export default function Home() {
  return (
    <main className="flex h-screen flex-col bg-[var(--color-background)]">
      <div className="flex-1 overflow-hidden">
        <ChatWindow />
      </div>
    </main>
  );
}
