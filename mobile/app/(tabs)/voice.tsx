import { useState, useCallback, useRef } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { colors } from "@/lib/theme";

const API_BASE = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

export default function VoiceScreen() {
  const [messages, setMessages] = useState<Message[]>([
    { id: "welcome", role: "assistant", content: "Hi! I'm Turbo, your AI assistant. I can help you manage notes, brainstorm ideas, do research, and create specs. What would you like to do?" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const flatListRef = useRef<FlatList>(null);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      // Build history from existing messages (exclude welcome)
      const history = messages
        .filter(m => m.id !== "welcome")
        .map(m => ({ role: m.role, content: m.content }));

      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.reply || "Done!",
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (e: any) {
      setMessages(prev => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: "assistant", content: `Error: ${e.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, messages]);

  const renderMessage = useCallback(({ item }: { item: Message }) => {
    const isUser = item.role === "user";
    return (
      <View style={[msgStyles.row, isUser ? msgStyles.rowUser : msgStyles.rowAgent]}>
        {!isUser && (
          <View style={msgStyles.avatar}>
            <LinearGradient
              colors={["#E91E8C", "#7B2FBE"]}
              style={msgStyles.avatarGradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
            >
              <Ionicons name="sparkles" size={14} color="#fff" />
            </LinearGradient>
          </View>
        )}
        <View style={[msgStyles.bubble, isUser ? msgStyles.bubbleUser : msgStyles.bubbleAgent]}>
          <Text style={[msgStyles.text, isUser ? msgStyles.textUser : msgStyles.textAgent]}>
            {item.content}
          </Text>
        </View>
      </View>
    );
  }, []);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      keyboardVerticalOffset={Platform.OS === "ios" ? 90 : 0}
    >
      {/* Header */}
      <View style={styles.header}>
        <LinearGradient
          colors={["#E91E8C", "#7B2FBE", "#00D4FF"]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.headerOrb}
        >
          <Ionicons name="chatbubbles" size={16} color="#fff" />
        </LinearGradient>
        <Text style={styles.headerTitle}>Turbo Chat</Text>
        <Text style={styles.headerSub}>AI Assistant</Text>
      </View>

      {/* Messages */}
      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderMessage}
        keyExtractor={item => item.id}
        style={styles.messageList}
        contentContainerStyle={styles.messageContent}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
      />

      {/* Loading indicator */}
      {loading && (
        <View style={styles.typingRow}>
          <ActivityIndicator size="small" color="#E91E8C" />
          <Text style={styles.typingText}>Turbo is thinking...</Text>
        </View>
      )}

      {/* Input */}
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="Ask Turbo anything..."
          placeholderTextColor={colors.dark.textMuted}
          multiline
          maxLength={2000}
          onSubmitEditing={sendMessage}
          returnKeyType="send"
          blurOnSubmit
        />
        <TouchableOpacity
          onPress={sendMessage}
          disabled={!input.trim() || loading}
          style={[styles.sendBtn, (!input.trim() || loading) && styles.sendBtnDisabled]}
        >
          <LinearGradient
            colors={input.trim() && !loading ? ["#E91E8C", "#7B2FBE"] : ["#333", "#333"]}
            style={styles.sendGradient}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
          >
            <Ionicons name="send" size={18} color="#fff" />
          </LinearGradient>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.dark.bgPrimary },
  header: {
    flexDirection: "row", alignItems: "center", gap: 10,
    paddingTop: Platform.OS === "ios" ? 56 : 16, paddingBottom: 12,
    paddingHorizontal: 16, borderBottomWidth: 1,
    borderBottomColor: "rgba(255,255,255,0.06)",
  },
  headerOrb: { width: 32, height: 32, borderRadius: 16, alignItems: "center", justifyContent: "center" },
  headerTitle: { fontSize: 17, fontWeight: "700", color: colors.dark.textPrimary },
  headerSub: { fontSize: 12, color: colors.dark.textMuted, marginLeft: "auto" },
  messageList: { flex: 1 },
  messageContent: { paddingHorizontal: 12, paddingVertical: 8, gap: 8 },
  typingRow: { flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 16, paddingVertical: 8 },
  typingText: { fontSize: 13, color: colors.dark.textMuted },
  inputRow: {
    flexDirection: "row", alignItems: "flex-end", gap: 8,
    paddingHorizontal: 12, paddingVertical: 10,
    borderTopWidth: 1, borderTopColor: "rgba(255,255,255,0.06)",
    paddingBottom: Platform.OS === "ios" ? 28 : 10,
  },
  input: {
    flex: 1, backgroundColor: "#1A1A2E", borderRadius: 20,
    paddingHorizontal: 16, paddingVertical: 10,
    color: colors.dark.textPrimary, fontSize: 15,
    maxHeight: 100, borderWidth: 1, borderColor: "rgba(255,255,255,0.08)",
  },
  sendBtn: {},
  sendBtnDisabled: { opacity: 0.4 },
  sendGradient: { width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center" },
});

const msgStyles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "flex-end", gap: 8 },
  rowUser: { justifyContent: "flex-end" },
  rowAgent: { justifyContent: "flex-start" },
  avatar: {},
  avatarGradient: { width: 28, height: 28, borderRadius: 14, alignItems: "center", justifyContent: "center" },
  bubble: { maxWidth: "78%", paddingHorizontal: 14, paddingVertical: 10, borderRadius: 18 },
  bubbleUser: { backgroundColor: "rgba(233,30,140,0.15)", borderBottomRightRadius: 4 },
  bubbleAgent: { backgroundColor: "#1A1A2E", borderBottomLeftRadius: 4 },
  text: { fontSize: 15, lineHeight: 21 },
  textUser: { color: colors.dark.textPrimary },
  textAgent: { color: colors.dark.textSecondary },
});
