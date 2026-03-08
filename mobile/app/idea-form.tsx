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
import { ideasApi } from "@/lib/api";
import { colors } from "@/lib/theme";

export default function IdeaFormScreen() {
  const params = useLocalSearchParams<{ id?: string; title?: string; description?: string }>();
  const isEditing = !!params.id;
  const router = useRouter();

  const [title, setTitle] = useState(params.title || "");
  const [description, setDescription] = useState(params.description || "");
  const [submitting, setSubmitting] = useState(false);

  const handleSave = async () => {
    if (!title.trim()) {
      Alert.alert("Error", "Title is required");
      return;
    }
    setSubmitting(true);
    try {
      if (isEditing && params.id) {
        await ideasApi.update(params.id, { title, description });
      } else {
        await ideasApi.create({ title, description });
      }
      router.back();
    } catch {
      Alert.alert("Error", "Failed to save idea");
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
          placeholder="Idea title"
          placeholderTextColor={colors.dark.textMuted}
          value={title}
          onChangeText={setTitle}
        />
        <TextInput
          style={styles.descInput}
          placeholder="Describe your idea..."
          placeholderTextColor={colors.dark.textMuted}
          value={description}
          onChangeText={setDescription}
          multiline
          textAlignVertical="top"
        />
        <TouchableOpacity
          style={[styles.saveButton, submitting && styles.disabled]}
          onPress={handleSave}
          disabled={submitting}
        >
          <Text style={styles.saveText}>
            {submitting ? "Saving..." : isEditing ? "Update Idea" : "Create Idea"}
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
  descInput: {
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
    backgroundColor: colors.brand.cyan,
    borderRadius: 10,
    padding: 16,
    alignItems: "center",
  },
  disabled: { opacity: 0.5 },
  saveText: { color: "#fff", fontSize: 16, fontWeight: "600" },
});
