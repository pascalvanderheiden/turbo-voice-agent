import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { notesApi } from "@/lib/api";
import { colors } from "@/lib/theme";

export default function NoteFormScreen() {
  const params = useLocalSearchParams<{ id?: string; title?: string; content?: string }>();
  const isEditing = !!params.id;
  const router = useRouter();

  const [title, setTitle] = useState(params.title || "");
  const [content, setContent] = useState(params.content || "");
  const [submitting, setSubmitting] = useState(false);

  const handleSave = async () => {
    if (!title.trim() || !content.trim()) {
      Alert.alert("Error", "Title and content are required");
      return;
    }

    setSubmitting(true);
    try {
      if (isEditing && params.id) {
        await notesApi.update(params.id, { title, content });
      } else {
        await notesApi.create({ title, content });
      }
      router.back();
    } catch {
      Alert.alert("Error", "Failed to save note");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <View style={styles.form}>
        <TextInput
          style={styles.titleInput}
          placeholder="Title"
          placeholderTextColor={colors.dark.textMuted}
          value={title}
          onChangeText={setTitle}
        />
        <TextInput
          style={styles.contentInput}
          placeholder="Content"
          placeholderTextColor={colors.dark.textMuted}
          value={content}
          onChangeText={setContent}
          multiline
          textAlignVertical="top"
        />
        <TouchableOpacity
          style={[styles.saveButton, submitting && styles.saveButtonDisabled]}
          onPress={handleSave}
          disabled={submitting}
        >
          <Text style={styles.saveButtonText}>
            {submitting ? "Saving..." : isEditing ? "Update Note" : "Create Note"}
          </Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.dark.bgPrimary },
  form: { flex: 1, padding: 16, gap: 12 },
  titleInput: {
    fontSize: 16,
    color: colors.dark.textPrimary,
    backgroundColor: colors.dark.bgSecondary,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.dark.border,
    padding: 14,
  },
  contentInput: {
    flex: 1,
    fontSize: 15,
    color: colors.dark.textPrimary,
    backgroundColor: colors.dark.bgSecondary,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.dark.border,
    padding: 14,
  },
  saveButton: {
    backgroundColor: colors.brand.pink,
    borderRadius: 10,
    padding: 16,
    alignItems: "center",
  },
  saveButtonDisabled: { opacity: 0.5 },
  saveButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
});
