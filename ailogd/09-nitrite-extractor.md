# JetBrains Copilot — Nitrite/H2 MVStore Java Extractor

The JetBrains Copilot plugin stores session data in Nitrite databases backed by H2 MVStore. These use Java-serialized objects that cannot be read directly from Python. A small Java program extracts data to JSONL.

---

## Database Details

### File Locations

```
~/.config/github-copilot/db/
├── chat-agent-sessions/*/copilot-agent-sessions-nitrite.db  (32KB)
├── chat-sessions/*/copilot-chat-nitrite.db                  (28KB)
└── chat-edit-sessions/*/copilot-edit-sessions-nitrite.db    (32KB)
```

### File Format

- **Format:** H2 MVStore version 3 (format 3, MVStore 2.2.224)
- **Value encoding:** Java-serialized objects via `ObjectOutputStream` (magic bytes `AC ED 00 05`)
- **Document type:** `NitriteDocument` objects (essentially `LinkedHashMap`)

### Collections

`NtChatSession`, `NtTurn`, `NtSelectedModel`, `NtAgentSession`, `NtAgentTurn`, `NtAgentWorkingSetItem`

### Entity Schema (decompiled from `core.jar`)

| Entity | Key Fields |
|--------|------------|
| `NtChatSession` | `id`, `name`, `projectName`, `user`, `createdAt`, `activeAt`, `modifiedAt`, `client`, `input` |
| `NtTurn` | `id`, `sessionId`, `createdAt`, `deletedAt`, `steps[]`, `request: NtMessage`, `response: NtMessage`, `rating` |
| `NtMessage` | `user`, `type`, `status`, `content`, `references`, `annotations`, `agent`, `model`, `createdAt`, `errorCode`, `errorReason` |
| `NtAgentSession` | `id`, `name`, `user`, `createdAt`, `activeAt`, `modifiedAt`, `input`, `turns[]`, `workingSet[]`, `welcomeMessageSetting` |
| `NtAgentTurn` | `id`, `sessionId`, `createdAt`, `deletedAt`, `request: NtAgentMessage`, `response: NtAgentMessage`, `rating` |

---

## NitriteExtractor.java

**Location:** `modules/ailogd/java/NitriteExtractor.java`

```java
import org.dizitart.no2.Nitrite;
import org.dizitart.no2.collection.NitriteCollection;
import org.dizitart.no2.collection.Document;
import org.dizitart.no2.mvstore.MVStoreModule;
import com.fasterxml.jackson.databind.ObjectMapper;

public class NitriteExtractor {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("Usage: NitriteExtractor <db_path>");
            System.exit(1);
        }

        String dbPath = args[0];
        ObjectMapper mapper = new ObjectMapper();

        // Open in read-only mode
        MVStoreModule storeModule = MVStoreModule.withConfig()
            .filePath(dbPath)
            .readOnly(true)
            .build();

        Nitrite db = Nitrite.builder()
            .loadModule(storeModule)
            .openOrCreate();

        try {
            // Get all collection names
            for (String collName : db.listCollectionNames()) {
                NitriteCollection coll = db.getCollection(collName);
                for (Document doc : coll.find()) {
                    // Add collection name to output
                    java.util.Map<String, Object> output = new java.util.LinkedHashMap<>();
                    output.put("_collection", collName);
                    // Document implements Map<String, Object>
                    for (var entry : doc) {
                        output.put(entry.getKey(), entry.getValue());
                    }
                    System.out.println(mapper.writeValueAsString(output));
                }
            }
        } finally {
            // Note: close() on read-only may throw in Nitrite < 4.2.1
            try {
                db.close();
            } catch (Exception e) {
                // Suppress read-only close exception (known Nitrite bug)
            }
        }
    }
}
```

---

## Required JARs

All available at: `/home/bs01763/.local/share/JetBrains/IntelliJIdea2025.3/github-copilot-intellij/lib/`

| JAR | Version | Purpose |
|-----|---------|---------|
| `nitrite-4.3.0.jar` | 4.3.0 | Nitrite core |
| `nitrite-mvstore-adapter-4.3.0.jar` | 4.3.0 | MVStore storage adapter |
| `nitrite-jackson-mapper-4.3.0.jar` | 4.3.0 | Jackson serialization for Nitrite |
| `h2-mvstore-2.2.224.jar` | **2.2.224** | H2 MVStore (exact version required) |
| `jackson-core-2.18.4.1.jar` | 2.18.4.1 | Jackson core |
| `jackson-databind-2.18.4.jar` | 2.18.4 | Jackson data binding |
| `jackson-annotations-2.18.4.jar` | 2.18.4 | Jackson annotations |
| `core.jar` | (plugin) | Copilot entity classes for deserialization |
| `kotlin-stdlib-2.0.0.jar` | 2.0.0 | Kotlin runtime (required by Copilot classes) |

**Java runtime:** `/usr/bin/java` (Java 25)

---

## Build & Run

### Compile

```bash
JETBRAINS_LIB="$HOME/.local/share/JetBrains/IntelliJIdea2025.3/github-copilot-intellij/lib"
CLASSPATH="$JETBRAINS_LIB/nitrite-4.3.0.jar:\
$JETBRAINS_LIB/nitrite-mvstore-adapter-4.3.0.jar:\
$JETBRAINS_LIB/nitrite-jackson-mapper-4.3.0.jar:\
$JETBRAINS_LIB/h2-mvstore-2.2.224.jar:\
$JETBRAINS_LIB/jackson-core-2.18.4.1.jar:\
$JETBRAINS_LIB/jackson-databind-2.18.4.jar:\
$JETBRAINS_LIB/jackson-annotations-2.18.4.jar:\
$JETBRAINS_LIB/core.jar:\
$JETBRAINS_LIB/kotlin-stdlib-2.0.0.jar"

javac -cp "$CLASSPATH" NitriteExtractor.java
```

### Run

```bash
java -cp "$CLASSPATH:." NitriteExtractor /path/to/copilot-chat-nitrite.db
```

**Output:** One JSON line per document to stdout:
```json
{"_collection": "NtChatSession", "id": "...", "name": "...", "projectName": "...", ...}
{"_collection": "NtTurn", "id": "...", "sessionId": "...", "request": {...}, "response": {...}, ...}
```

---

## Python Integration

```python
import subprocess
import shutil
import tempfile
import json
from pathlib import Path

JETBRAINS_LIB = Path.home() / ".local/share/JetBrains/IntelliJIdea2025.3/github-copilot-intellij/lib"
EXTRACTOR_DIR = Path(__file__).parent.parent.parent / "java"

def build_classpath() -> str:
    jars = [
        "nitrite-4.3.0.jar",
        "nitrite-mvstore-adapter-4.3.0.jar",
        "nitrite-jackson-mapper-4.3.0.jar",
        "h2-mvstore-2.2.224.jar",
        "jackson-core-2.18.4.1.jar",
        "jackson-databind-2.18.4.jar",
        "jackson-annotations-2.18.4.jar",
        "core.jar",
        "kotlin-stdlib-2.0.0.jar",
    ]
    return ":".join(str(JETBRAINS_LIB / jar) for jar in jars)

def extract_nitrite(db_path: Path) -> list[dict]:
    """Extract all documents from a Nitrite DB as dicts."""
    # Copy to avoid lock conflicts
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        shutil.copy2(db_path, tmp.name)
        tmp_path = tmp.name

    try:
        classpath = f"{build_classpath()}:{EXTRACTOR_DIR}"
        result = subprocess.run(
            ["/usr/bin/java", "-cp", classpath, "NitriteExtractor", tmp_path],
            capture_output=True, text=True, timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(f"NitriteExtractor failed: {result.stderr}")

        docs = []
        for line in result.stdout.strip().split("\n"):
            if line:
                docs.append(json.loads(line))
        return docs
    finally:
        Path(tmp_path).unlink(missing_ok=True)
```

---

## Critical Gotchas

### h2-mvstore Version Pinning

**Must use h2-mvstore 2.2.224 exactly.** The Copilot databases are format version 3. h2-mvstore 2.4.x uses format version 4 and **cannot read** format 3 files. Error message:

```
org.h2.mvstore.MVStoreException: The file format is not supported
```

The install script should verify the h2-mvstore version by checking the DB file header.

### DB Locking

The Nitrite database is locked while IntelliJ/PyCharm is running. Attempting to open it directly will fail or corrupt data.

**Solution:** Always copy the DB file to a temp location before extraction:
```python
shutil.copy2(db_path, tmp_path)  # atomic copy
# Extract from tmp_path
os.unlink(tmp_path)  # cleanup
```

### Read-Only Close Bug (Nitrite < 4.2.1)

In Nitrite versions before 4.2.1, calling `getCollection()` on a read-only database incorrectly marks the store as dirty. When `close()` is called, it attempts a commit on the read-only store, throwing:

```
org.h2.mvstore.MVStoreException: This store is read-only
```

**Workaround:** Catch and suppress the exception during `close()` (as shown in the Java code above).

### Entity Classes

The `core.jar` from the Copilot plugin contains the entity classes (`NtChatSession`, `NtTurn`, etc.) needed for proper deserialization. Without these on the classpath, documents may not deserialize correctly.

### JetBrains Updates

When JetBrains IDEs update, the Copilot plugin JARs may move to a new path (e.g., `IntelliJIdea2026.1` instead of `2025.3`). The `config.yaml` stores the resolved path, and `install.sh --doctor` detects and warns about missing JARs.

### Small Data Volume

The JetBrains Copilot databases are very small (~92KB total across 3 files). The 60-second polling interval is appropriate — the overhead of copying + Java subprocess is disproportionate for the small data volume.
