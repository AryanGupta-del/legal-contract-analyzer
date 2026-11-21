import { useState } from "react";
import Landing from "./components/Landing";
import Workspace from "./components/Workspace";
import type { DocInfo } from "./types";

export default function App() {
  const [doc, setDoc] = useState<DocInfo | null>(null);
  return doc ? <Workspace key={doc.id} doc={doc} onReset={() => setDoc(null)} /> : <Landing onReady={setDoc} />;
}
