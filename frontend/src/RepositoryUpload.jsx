import { useState } from "react";
import API from "./api";

function RepositoryUpload() {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [message, setMessage] = useState("");

    const handleFileChange = (event) => {
        const selectedFile = event.target.files[0];

        if (!selectedFile) {
            return;
        }

        if (!selectedFile.name.toLowerCase().endsWith(".zip")) {
            setFile(null);
            setMessage("Please select a ZIP file.");
            return;
        }

        setFile(selectedFile);
        setMessage("");
    };

    const handleUpload = async () => {
        if (!file) {
            setMessage("Please select a ZIP file first.");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        try {
            setUploading(true);
            setMessage("");

            const response = await API.post(
                "/api/repository/upload",
                formData
            );

            setMessage(response.data.message);
        } catch (error) {
            console.error("Upload failed:", error);

            if (error.response) {
                setMessage(
                    error.response.data.detail || "Upload failed."
                );
            } else {
                setMessage("Could not connect to the backend.");
            }
        } finally {
            setUploading(false);
        }
    };

    return (
        <div>
            <h2>Upload Repository</h2>

            <input
                type="file"
                accept=".zip"
                onChange={handleFileChange}
            />

            {file && (
                <p>
                    Selected: <strong>{file.name}</strong>
                </p>
            )}

            <button
                onClick={handleUpload}
                disabled={uploading}
            >
                {uploading ? "Uploading..." : "Upload Repository"}
            </button>

            {message && <p>{message}</p>}
        </div>
    );
}

export default RepositoryUpload;