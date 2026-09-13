import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BookmarkIcon,
  MessageSquarePlusIcon,
  MicIcon,
  PaperclipIcon,
  SendIcon,
  SparklesIcon,
  StarIcon } from
'lucide-react';
import { Badge, Button, Card } from '../components/ui/Primitives';
import { MarkdownContent } from '../components/MarkdownContent';
import { suggestedPrompts } from '../data/content';
import { sendAssistantMessage } from '../services/atlasApi';
import { ChatCard, ChatMessage, Conversation } from '../types';
import { useAtlas } from '../contexts/AtlasContext';
import { cn, inr, timeNow, uid } from '../utils/format';

const seedConversations: Conversation[] = [
{ id: 'c1', title: 'Goa Trip', updated: 'Today', messages: [] },
{ id: 'c2', title: 'Weekend in Manali', updated: 'Yesterday', messages: [] },
{ id: 'c3', title: 'Budget Trip', updated: '3 days ago', messages: [] },
{ id: 'c4', title: 'Japan Planning', updated: 'Last week', messages: [] }];


type VoiceState = 'idle' | 'listening' | 'processing' | 'responding';

function TravelCard({ card }: {card: ChatCard;}) {
  const { toast } = useAtlas();
  return (
    <div className="flex w-[230px] shrink-0 flex-col overflow-hidden rounded-xl border border-line bg-surface">
      {card.image && <img src={card.image} alt="" className="h-24 w-full object-cover" />}
      <div className="flex flex-1 flex-col p-3">
        <div className="flex items-start justify-between gap-2">
          <p className="text-[13.5px] font-bold text-ink">{card.title}</p>
          {card.rating &&
          <span className="inline-flex items-center gap-0.5 text-[12px] font-semibold text-ink">
              <StarIcon className="h-3 w-3 fill-warning text-warning" />
              {card.rating}
            </span>
          }
        </div>
        <p className="mt-0.5 text-[12px] leading-snug text-muted">{card.subtitle}</p>
        <p className="mt-1.5 text-[11.5px] text-muted">{card.meta}</p>
        {typeof card.price === 'number' && <p className="mt-1 text-[12.5px] font-semibold text-brand">{inr(card.price)}</p>}
        <div className="mt-3 flex gap-1.5">
          <button
            onClick={() => toast({ title: 'Added to trip', description: card.title, tone: 'success' })}
            className="flex-1 rounded-lg bg-brand px-2 py-1.5 text-[11.5px] font-semibold text-white">
            
            Add to Trip
          </button>
          <button
            onClick={() => toast({ title: 'Saved', description: card.title, tone: 'success' })}
            aria-label={`Save ${card.title}`}
            className="rounded-lg border border-line px-2 py-1.5 text-muted hover:text-ink">
            
            <BookmarkIcon className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>);

}

export function AssistantPage() {
  const [conversations, setConversations] = useState(seedConversations);
  const [activeId, setActiveId] = useState('c1');
  const [messages, setMessages] = useState<ChatMessage[]>([
  {
    id: 'm0',
    role: 'assistant',
    content: "Hi, I'm ATLAS. Where are you planning to go?",
    time: timeNow()
  }]
  );
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [voice, setVoice] = useState<VoiceState>('idle');
  const endRef = useRef<HTMLDivElement>(null);
  const { toast } = useAtlas();

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, typing]);

  const send = async (text: string) => {
    const value = text.trim();
    if (!value || typing) return;
    setMessages((prev) => [...prev, { id: uid('m'), role: 'user', content: value, time: timeNow() }]);
    setInput('');
    setTyping(true);
    const reply = await sendAssistantMessage(value);
    setMessages((prev) => [...prev, reply]);
    setTyping(false);
  };

  const startVoice = () => {
    if (voice !== 'idle') {
      setVoice('idle');
      return;
    }
    setVoice('listening');
    window.setTimeout(() => setVoice('processing'), 1600);
    window.setTimeout(() => {
      setVoice('responding');
      send('Find hidden gems near my hotel');
    }, 2600);
    window.setTimeout(() => setVoice('idle'), 4200);
  };

  const voiceLabel: Record<VoiceState, string> = {
    idle: 'Tap to speak',
    listening: 'Listening…',
    processing: 'Processing your request…',
    responding: 'ATLAS is responding…'
  };

  return (
    <div className="flex h-[calc(100vh-72px)] w-full">
      <aside className="hidden w-[268px] shrink-0 flex-col border-r border-line bg-surface md:flex">
        <div className="border-b border-line p-4">
          <Button
            className="w-full"
            icon={<MessageSquarePlusIcon className="h-4 w-4" />}
            onClick={() => {
              const conversation = { id: uid('c'), title: 'New conversation', updated: 'Just now', messages: [] };
              setConversations((prev) => [conversation, ...prev]);
              setActiveId(conversation.id);
              setMessages([{ id: uid('m'), role: 'assistant', content: "Hi, I'm ATLAS. Where are you planning to go?", time: timeNow() }]);
            }}>
            
            New chat
          </Button>
        </div>
        <div className="atlas-scroll flex-1 overflow-y-auto p-3">
          <p className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Conversations</p>
          <ul className="space-y-1">
            {conversations.map((c) =>
            <li key={c.id}>
                <button
                onClick={() => setActiveId(c.id)}
                className={cn(
                  'w-full rounded-xl px-3 py-2.5 text-left transition-colors',
                  c.id === activeId ? 'bg-brand/10' : 'hover:bg-subtle'
                )}>
                
                  <span className={cn('block text-[13.5px] font-medium', c.id === activeId ? 'text-brand' : 'text-ink')}>
                    {c.title}
                  </span>
                  <span className="block text-[11.5px] text-muted">{c.updated}</span>
                </button>
              </li>
            )}
          </ul>
        </div>
        <div className="border-t border-line p-4">
          <Card className="bg-canvas p-3 shadow-none">
            <p className="text-[12.5px] font-semibold text-ink">Agents connected</p>
            <p className="mt-1 text-[11.5px] leading-relaxed text-muted">
              Planner, Food, Weather and Review Intelligence agents are active in this chat.
            </p>
          </Card>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col bg-canvas">
        <header className="flex items-center justify-between gap-4 border-b border-line bg-surface px-5 py-3.5">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-white">
              <SparklesIcon className="h-4.5 w-4.5" />
            </span>
            <div>
              <p className="text-[14.5px] font-bold text-ink">ATLAS Assistant</p>
              <p className="text-[12px] text-muted">Multi-agent · online</p>
            </div>
          </div>
          <Badge tone="success">Live</Badge>
        </header>

        <div className="atlas-scroll flex-1 overflow-y-auto px-4 py-6 sm:px-8">
          <div className="mx-auto max-w-3xl space-y-5">
            {messages.map((m) =>
            <motion.div
              key={m.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn('flex', m.role === 'user' ? 'justify-end' : 'justify-start')}>
              
                <div className={cn('max-w-[85%]', m.role === 'user' && 'items-end')}>
                  <div
                  className={cn(
                    'rounded-2xl px-4 py-3 text-[14px] leading-relaxed',
                    m.role === 'user' ?
                    'rounded-br-md bg-brand text-white' :
                    'rounded-bl-md border border-line bg-surface text-ink'
                  )}>
                  
                    {m.role === 'user' ? (
                      m.content
                    ) : (
                      <MarkdownContent>{m.content}</MarkdownContent>
                    )}
                  </div>
                  {m.cards &&
                <div className="no-scrollbar mt-3 flex gap-3 overflow-x-auto pb-1">
                      {m.cards.map((card, i) =>
                  <TravelCard key={`${m.id}-${i}`} card={card} />
                  )}
                    </div>
                }
                  <p className={cn('mt-1 text-[11px] text-muted', m.role === 'user' && 'text-right')}>{m.time}</p>
                </div>
              </motion.div>
            )}

            {typing &&
            <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md border border-line bg-surface px-4 py-3.5 w-fit">
                {[0, 1, 2].map((i) =>
              <motion.span
                key={i}
                animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }}
                transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
                className="h-1.5 w-1.5 rounded-full bg-brand" />

              )}
                <span className="ml-1.5 text-[12.5px] text-muted">Agents are working…</span>
              </div>
            }

            {messages.length <= 1 &&
            <div className="pt-2">
                <p className="text-[12.5px] font-semibold text-muted">Suggested prompts</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {suggestedPrompts.map((prompt) =>
                <button
                  key={prompt}
                  onClick={() => send(prompt)}
                  className="rounded-full border border-line bg-surface px-3.5 py-2 text-[13px] text-muted transition-colors hover:border-brand/40 hover:text-brand">
                  
                      {prompt}
                    </button>
                )}
                </div>
              </div>
            }
            <div ref={endRef} />
          </div>
        </div>

        <div className="border-t border-line bg-surface px-4 py-4 sm:px-8">
          <div className="mx-auto max-w-3xl">
            <AnimatePresence>
              {voice !== 'idle' &&
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mb-3 flex items-center gap-3 rounded-xl border border-brand/30 bg-brand/5 px-4 py-3">
                
                  <span className="relative flex h-8 w-8 items-center justify-center rounded-full bg-brand text-white">
                    <MicIcon className="h-4 w-4" />
                    {voice === 'listening' &&
                  <motion.span
                    animate={{ scale: [1, 1.6], opacity: [0.5, 0] }}
                    transition={{ duration: 1.2, repeat: Infinity }}
                    className="absolute inset-0 rounded-full bg-brand" />

                  }
                  </span>
                  <p className="text-[13px] font-medium text-brand">{voiceLabel[voice]}</p>
                </motion.div>
              }
            </AnimatePresence>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                send(input);
              }}
              className="flex items-center gap-2 rounded-2xl border border-line bg-canvas p-2">
              
              <button
                type="button"
                aria-label="Attach a file"
                onClick={() => toast({ title: 'Attachment', description: 'File attachments are mocked in this prototype.', tone: 'info' })}
                className="flex h-10 w-10 items-center justify-center rounded-xl text-muted hover:bg-subtle hover:text-ink">
                
                <PaperclipIcon className="h-4.5 w-4.5" />
              </button>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message..."
                aria-label="Message ATLAS"
                className="h-10 min-w-0 flex-1 bg-transparent text-[14px] text-ink placeholder:text-muted/80 focus:outline-none" />
              
              <button
                type="button"
                onClick={startVoice}
                aria-label="Voice input"
                aria-pressed={voice !== 'idle'}
                className={cn(
                  'flex h-10 w-10 items-center justify-center rounded-xl transition-colors',
                  voice === 'idle' ? 'text-muted hover:bg-subtle hover:text-ink' : 'bg-brand/10 text-brand'
                )}>
                
                <MicIcon className="h-4.5 w-4.5" />
              </button>
              <button
                type="submit"
                aria-label="Send message"
                disabled={!input.trim() || typing}
                className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand text-white transition-transform disabled:opacity-40 active:scale-95">
                
                <SendIcon className="h-4 w-4" />
              </button>
            </form>
            <p className="mt-2 text-center text-[11.5px] text-muted">
              ATLAS AI is powered by Gemini · Suggestions are not confirmed bookings
            </p>
          </div>
        </div>
      </div>
    </div>);

}
