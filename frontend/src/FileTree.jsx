import { useState } from "react";

function TreeNode({ name, children, level }) {
    const [isOpen, setIsOpen] = useState(true);

    const isFile = children === null;

    if (isFile) {
        return (
            <div
                style={{
                    marginLeft: `${level * 20}px`,
                    padding: "5px 0",
                    cursor: "default",
                }}
            >
                📄 {name}
            </div>
        );
    }

    return (
        <div>
            <div
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    marginLeft: `${level * 20}px`,
                    padding: "5px 0",
                    cursor: "pointer",
                    userSelect: "none",
                }}
            >
                {isOpen ? "▾ 📁" : "▸ 📁"} {name}
            </div>

            {isOpen && (
                <div>
                    {Object.entries(children).map(
                        ([childName, childChildren]) => (
                            <TreeNode
                                key={childName}
                                name={childName}
                                children={childChildren}
                                level={level + 1}
                            />
                        )
                    )}
                </div>
            )}
        </div>
    );
}

function FileTree({ files }) {
    const tree = {};

    files.forEach((filePath) => {
        const parts = filePath.split("/");

        let current = tree;

        parts.forEach((part, index) => {
            const isFile = index === parts.length - 1;

            if (!current[part]) {
                current[part] = isFile ? null : {};
            }

            if (!isFile) {
                current = current[part];
            }
        });
    });

    return (
        <div>
            {Object.entries(tree).map(([name, children]) => (
                <TreeNode
                    key={name}
                    name={name}
                    children={children}
                    level={0}
                />
            ))}
        </div>
    );
}

export default FileTree;