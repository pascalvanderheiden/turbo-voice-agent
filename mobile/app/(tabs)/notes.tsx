import { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  Alert,
} from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { notesApi, type Note } from "@/lib/api";
import { colors } from "@/lib/theme";

export default function NotesScreen() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const loadNotes = useCallback(async () => {
    try {
      setLoading(true);
      const data = await notesApi.list();
      setNotes(data);
    } catch {
      Alert.alert("Error", "Failed to load notes");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  const handleDelete = (note: Note) => {
    Alert.alert("Delete Note", `Delete "${note.title}"?`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          await notesApi.delete(note.id);
          loadNotes();
        },
      },
    ]);
  };

  return (
    <View style={styles.container}>
      <FlatList
        data={notes}
        keyExtractor={(item) => item.id}
        refreshControl={
          <RefreshControl
            refreshing={loading}
            onRefresh={loadNotes}
            tintColor={colors.brand.pink}
          />
        }
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !loading ? (
            <View style={styles.empty}>
              <Text style={styles.emptyText}>No notes yet</Text>
              <Text style={styles.emptySubtext}>
                Create your first note or use voice mode
              </Text>
            </View>
          ) : null
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.noteCard}
            onPress={() =>
              router.push({
                pathname: "/note-form",
                params: { id: item.id, title: item.title, content: item.content },
              })
            }
            onLongPress={() => handleDelete(item)}
          >
            <Text style={styles.noteTitle} numberOfLines={1}>
              {item.title}
            </Text>
            <Text style={styles.noteContent} numberOfLines={2}>
              {item.content}
            </Text>
            <Text style={styles.noteDate}>
              {new Date(item.updatedAt).toLocaleDateString()}
            </Text>
          </TouchableOpacity>
        )}
      />

      <TouchableOpacity
        style={styles.fab}
        onPress={() => router.push("/note-form")}
      >
        <Ionicons name="add" size={28} color="#fff" />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.dark.bgPrimary },
  list: { padding: 16, gap: 12 },
  noteCard: {
    padding: 16,
    backgroundColor: colors.dark.bgCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.dark.border,
  },
  noteTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: colors.dark.textPrimary,
    marginBottom: 4,
  },
  noteContent: {
    fontSize: 14,
    color: colors.dark.textSecondary,
    marginBottom: 8,
  },
  noteDate: {
    fontSize: 12,
    color: colors.dark.textMuted,
  },
  empty: { alignItems: "center", paddingTop: 100 },
  emptyText: { fontSize: 16, color: colors.dark.textSecondary },
  emptySubtext: { fontSize: 13, color: colors.dark.textMuted, marginTop: 4 },
  fab: {
    position: "absolute",
    right: 20,
    bottom: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.brand.pink,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: colors.brand.pink,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
});
