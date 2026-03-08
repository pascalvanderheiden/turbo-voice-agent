"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

export interface Notification {
  id: string;
  title: string;
  timestamp: number;
  read: boolean;
}

interface Toast {
  id: string;
  title: string;
  exiting: boolean;
}

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (title: string) => void;
  markAllRead: () => void;
  clearAll: () => void;
}

const NotificationContext = createContext<NotificationContextType>({
  notifications: [],
  unreadCount: 0,
  addNotification: () => {},
  markAllRead: () => {},
  clearAll: () => {},
});

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, exiting: true } : t)));
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 400);
  }, []);

  const addNotification = useCallback((title: string) => {
    const id = `notif-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    setNotifications((prev) =>
      [{ id, title, timestamp: Date.now(), read: false }, ...prev].slice(0, 50)
    );
    setToasts((prev) => [...prev, { id, title, exiting: false }].slice(-3));
    const timer = setTimeout(() => dismissToast(id), 3000);
    timersRef.current.set(id, timer);
  }, [dismissToast]);

  const markAllRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  useEffect(() => {
    const timers = timersRef.current;
    return () => { timers.forEach((t) => clearTimeout(t)); };
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <NotificationContext.Provider value={{ notifications, unreadCount, addNotification, markAllRead, clearAll }}>
      {children}
      {/* iOS-style toast banners */}
      <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[100] flex flex-col items-center gap-2 pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto toast-banner ${toast.exiting ? "toast-exit" : "toast-enter"}`}
            onClick={() => dismissToast(toast.id)}
          >
            <div className="toast-pill">
              <div className="toast-indicator" />
              <span className="toast-text">{toast.title}</span>
            </div>
          </div>
        ))}
      </div>
      <style jsx>{`
        .toast-banner {
          cursor: pointer;
        }
        .toast-pill {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 12px 20px;
          border-radius: 16px;
          background: var(--color-bg-card);
          border: 1px solid var(--color-border-dark);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          box-shadow:
            0 8px 32px rgba(0, 0, 0, 0.2),
            0 2px 8px rgba(0, 0, 0, 0.1);
          max-width: 360px;
          min-width: 200px;
        }
        .toast-indicator {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--color-brand-pink);
          flex-shrink: 0;
        }
        .toast-text {
          font-size: 13px;
          font-weight: 500;
          color: var(--color-text-primary);
          line-height: 1.3;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .toast-enter {
          animation: toast-in 0.35s cubic-bezier(0.21, 1.02, 0.73, 1) forwards;
        }
        .toast-exit {
          animation: toast-out 0.35s cubic-bezier(0.36, 0, 0.66, -0.56) forwards;
        }
        @keyframes toast-in {
          from { opacity: 0; transform: translateY(-20px) scale(0.9); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes toast-out {
          from { opacity: 1; transform: translateY(0) scale(1); }
          to { opacity: 0; transform: translateY(-20px) scale(0.9); }
        }
      `}</style>
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  return useContext(NotificationContext);
}
