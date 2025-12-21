/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef, onWillStart } from "@odoo/owl";

export class OfficeDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.fileInput = useRef("fileInput");
        this.renameInput = useRef("renameInput");
        
        this.state = useState({
            recentDocuments: [],
            starredDocuments: [],
            sharedDocuments: [],
            storageStats: {},
            searchQuery: "",
            viewMode: "grid", // grid or list
            activeTab: "recent", // recent, starred, shared, folders
            isLoading: true,
            folders: [],
            currentFolder: null,
            dragOver: false,
            renameModal: { visible: false, docId: null, name: '' },
            folderPath: [],
            folderDocuments: [],
            folderModal: { visible: false, parentId: null, name: '' },
            folderExpanded: {},
            moveModal: { visible: false, docId: null, targetFolderId: null },
            shareModal: { visible: false, docId: null, url: '', permission: 'view', active: false },
            draggingDocId: null,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.isLoading = true;
        try {
            const currentFolderId = this.state.currentFolder ? this.state.currentFolder.id : false;
            const [recentDocs, starredDocs, sharedDocs, stats, folders, folderDocs, folderPath] = await Promise.all([
                this.orm.call("office.document", "get_recent_documents", [20]),
                this.orm.call("office.document", "get_starred_documents", []),
                this.orm.call("office.document", "get_shared_with_me", []),
                this.orm.call("office.document", "get_storage_stats", []),
                this.orm.call("office.folder", "get_folder_tree", [false]),
                this.orm.call("office.document", "get_documents_in_folder", [currentFolderId]),
                currentFolderId ? this.orm.call("office.folder", "get_folder_path", [currentFolderId]) : [],
            ]);
            
            this.state.recentDocuments = recentDocs;
            this.state.starredDocuments = starredDocs;
            this.state.sharedDocuments = sharedDocs;
            this.state.storageStats = stats;
            this.state.folders = folders;
            this.state.folderDocuments = folderDocs;
            this.state.folderPath = folderPath || [];
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.notification.add("Failed to load dashboard data", { type: "danger" });
        }
        this.state.isLoading = false;
    }

    async createDocument(docType) {
        try {
            this.notification.add("Creating document...", { type: "info" });
            
            const folderId = this.state.currentFolder ? this.state.currentFolder.id : false;
            const result = await this.orm.call("office.document", "create_document_from_template", [docType, folderId]);
            
            this.notification.add("Document created! Opening editor...", { type: "success" });
            
            // Open the editor directly
            const action = await this.orm.call("office.document", "action_open_editor", [[result.document_id]]);
            this.action.doAction(action);
            
        } catch (error) {
            console.error("Error creating document:", error);
            this.notification.add("Failed to create document: " + (error.message || error.data?.message || "Unknown error"), {
                type: "danger",
            });
        }
    }

    async openDocument(documentId) {
        try {
            const action = await this.orm.call("office.document", "action_open_editor", [[documentId]]);
            this.action.doAction(action);
        } catch (error) {
            console.error("Error opening document:", error);
            this.notification.add("Failed to open document", { type: "danger" });
        }
    }

    async toggleStar(documentId, event) {
        event.stopPropagation();
        try {
            await this.orm.call("office.document", "action_toggle_star", [[documentId]]);
            await this.loadDashboardData();
        } catch (error) {
            console.error("Error toggling star:", error);
        }
    }

    async deleteDocument(documentId, event) {
        event.stopPropagation();
        try {
            await this.orm.call("office.document", "action_move_to_trash", [[documentId]]);
            this.notification.add("Document moved to trash", { type: "warning" });
            await this.loadDashboardData();
        } catch (error) {
            console.error("Error deleting document:", error);
        }
    }

    async duplicateDocument(documentId, event) {
        event && event.stopPropagation();
        try {
            this.notification.add("Creating copy...", { type: "info" });
            await this.orm.call("office.document", "action_duplicate", [[documentId]]);
            this.notification.add("Document copied successfully!", { type: "success" });
            await this.loadDashboardData();
        } catch (error) {
            console.error("Error duplicating document:", error);
            const msg = error.data?.message || error.message || "Unknown error";
            this.notification.add("Failed to copy document: " + msg, { type: "danger" });
        }
    }

    async renameDocument(documentId, event) {
        // kept for backward compatibility; opens modal instead
        this.openRenameModal(documentId, event);
    }

    async openShare(documentId, event) {
        event && event.stopPropagation();
        try {
            let action = await this.orm.call('office.document', 'action_share', [[documentId]]);
            if (!action) {
                this.notification.add('No action returned from server for share dialog', { type: 'warning' });
                return;
            }

            // sometimes RPC returns an array or unexpected structure; validate
            if (Array.isArray(action) && action.length === 1) {
                // unpack if wrapped
                action = action[0];
            }

            if (!action || typeof action !== 'object' || !action.type) {
                // action may still be a plain action dict without a 'type' in some cases
                try {
                    this.action.doAction(action);
                } catch (err) {
                    console.error('Unexpected action shape for share:', action, err);
                    this.notification.add('Unable to open share dialog (unexpected server response)', { type: 'danger' });
                }
                return;
            }

            try {
                await this.action.doAction(action);
            } catch (err) {
                console.error('doAction failed for share action:', action, err);
                this.notification.add('Failed to open share dialog', { type: 'danger' });
            }
        } catch (error) {
            console.error('Error opening share wizard:', error);
            this.notification.add('Failed to open share dialog', { type: 'danger' });
        }
    }

    openRenameModal(documentId, event) {
        event && event.stopPropagation();
        // find document name from available lists
        const all = [
            ...this.state.recentDocuments,
            ...this.state.starredDocuments,
            ...this.state.sharedDocuments,
            ...this.state.folderDocuments,
        ];
        const doc = all.find(d => d.id === documentId) || null;
        this.state.renameModal.visible = true;
        this.state.renameModal.docId = documentId;
        this.state.renameModal.name = doc ? doc.name : '';
        setTimeout(() => {
            this.renameInput.el && this.renameInput.el.focus();
        }, 50);
    }

    closeRenameModal() {
        this.state.renameModal.visible = false;
        this.state.renameModal.docId = null;
        this.state.renameModal.name = '';
    }

    async submitRename() {
        const { docId, name } = this.state.renameModal;
        if (!name || !name.trim()) {
            this.notification.add('Name cannot be empty', { type: 'warning' });
            return;
        }
        try {
            const action = await this.orm.call('office.document', 'action_rename', [[docId], name.trim()]);
            if (action) {
                try {
                    await this.action.doAction(action);
                } catch (err) {
                    // non-fatal: log and continue
                    console.error('doAction failed after rename:', err, 'action:', action);
                }
            }
            this.closeRenameModal();
            await this.loadDashboardData();
        } catch (error) {
            console.error('Error renaming document:', error);
            const msg = error.data?.message || error.message || 'Unknown error';
            this.notification.add('Failed to rename document: ' + msg, { type: 'danger' });
        }
    }

    async searchDocuments() {
        if (!this.state.searchQuery.trim()) {
            await this.loadDashboardData();
            return;
        }
        
        try {
            const results = await this.orm.call("office.document", "search_documents", [
                this.state.searchQuery,
                false,  // doc_type
                false,  // folder_id
                false,  // starred_only
            ]);
            this.state.recentDocuments = results;
            this.state.activeTab = "search";
        } catch (error) {
            console.error("Error searching:", error);
        }
    }

    onSearchInput(event) {
        this.state.searchQuery = event.target.value;
        // Debounced search
        clearTimeout(this._searchTimeout);
        this._searchTimeout = setTimeout(() => this.searchDocuments(), 300);
    }

    onSearchKeydown(event) {
        if (event.key === "Enter") {
            this.searchDocuments();
        }
    }

    clearSearch() {
        this.state.searchQuery = "";
        this.state.activeTab = "recent";
        this.loadDashboardData();
    }

    setActiveTab(tab) {
        this.state.activeTab = tab;
        if (tab === 'folders') {
            this.loadFolderContext(this.state.currentFolder ? this.state.currentFolder.id : false);
        }
    }

    setViewMode(mode) {
        this.state.viewMode = mode;
    }

    getActiveDocuments() {
        switch (this.state.activeTab) {
            case "starred":
                return this.state.starredDocuments;
            case "shared":
                return this.state.sharedDocuments;
            case "folders":
                return this.state.folderDocuments;
            case "search":
            case "recent":
            default:
                return this.state.recentDocuments;
        }
    }

    getTabTitle() {
        switch (this.state.activeTab) {
            case "starred":
                return "Starred";
            case "shared":
                return "Shared with me";
            case "search":
                return `Search results for "${this.state.searchQuery}"`;
            case "recent":
            default:
                return "Recent documents";
        }
    }

    formatDate(dateStr) {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) return "Just now";
        if (diffMins < 60) return `${diffMins} min ago`;
        if (diffHours < 24) return `${diffHours} hours ago`;
        if (diffDays < 7) return `${diffDays} days ago`;
        
        return date.toLocaleDateString();
    }

    getDocIcon(docType) {
        const icons = {
            word: "fa-file-word-o",
            excel: "fa-file-excel-o",
            powerpoint: "fa-file-powerpoint-o",
            pdf: "fa-file-pdf-o",
            text: "fa-file-text-o",
        };
        return icons[docType] || "fa-file-o";
    }

    getDocColor(docType) {
        const colors = {
            word: "#2B5797",
            excel: "#217346",
            powerpoint: "#D24726",
            pdf: "#E74C3C",
            text: "#7F8C8D",
        };
        return colors[docType] || "#875A7B";
    }

    // ---------- Folder helpers ----------
    flattenFolders(folders, level = 0) {
        const rows = [];
        folders.forEach((f) => {
            rows.push({ ...f, level });
            if (f.children && f.children.length) {
                // Only expand children if the folder is marked expanded in state
                if (this.state.folderExpanded[f.id]) {
                    rows.push(...this.flattenFolders(f.children, level + 1));
                }
            }
        });
        return rows;
    }

    findFolderById(folders, id) {
        for (const f of folders) {
            if (f.id === id) return f;
            if (f.children) {
                const found = this.findFolderById(f.children, id);
                if (found) return found;
            }
        }
        return null;
    }

    async loadFolderContext(folderId = false) {
        this.state.isLoading = true;
        try {
            const [folders, folderDocs, folderPath] = await Promise.all([
                this.orm.call("office.folder", "get_folder_tree", [false]),
                this.orm.call("office.document", "get_documents_in_folder", [folderId || false]),
                folderId ? this.orm.call("office.folder", "get_folder_path", [folderId]) : [],
            ]);
            this.state.folders = folders;
            // reset expanded map for folders (collapsed by default)
            this.state.folderExpanded = {};
            this.state.folderDocuments = folderDocs;
            this.state.folderPath = folderPath || [];
            this.state.currentFolder = folderId ? this.findFolderById(folders, folderId) || { id: folderId } : null;
        } catch (error) {
            console.error('Error loading folder context', error);
            this.notification.add('Failed to load folder data', { type: 'danger' });
        }
        this.state.isLoading = false;
    }

    toggleFolderExpand(folderId, ev) {
        ev && ev.stopPropagation();
        const current = this.state.folderExpanded[folderId];
        // toggle
        this.state.folderExpanded[folderId] = !current;
    }

    async selectFolder(folderId) {
        this.state.activeTab = 'folders';
        await this.loadFolderContext(folderId);
    }

    openFolderModal(parentId = null) {
        this.state.folderModal.visible = true;
        this.state.folderModal.parentId = parentId;
        this.state.folderModal.name = '';
    }

    closeFolderModal() {
        this.state.folderModal.visible = false;
        this.state.folderModal.parentId = null;
        this.state.folderModal.name = '';
    }

    async submitCreateFolder() {
        const { name, parentId } = this.state.folderModal;
        if (!name || !name.trim()) {
            this.notification.add('Folder name cannot be empty', { type: 'warning' });
            return;
        }
        try {
            await this.orm.call('office.folder', 'create_folder', [name.trim(), parentId || false]);
            this.closeFolderModal();
            await this.loadFolderContext(parentId || (this.state.currentFolder ? this.state.currentFolder.id : false));
            this.notification.add('Folder created', { type: 'success' });
        } catch (error) {
            console.error('Error creating folder', error);
            const msg = error.data?.message || error.message || 'Unknown error';
            this.notification.add('Failed to create folder: ' + msg, { type: 'danger' });
        }
    }

    async moveDocumentToFolder(docId, targetFolderId) {
        try {
            await this.orm.call('office.document', 'move_document', [docId, targetFolderId || false]);
            await this.loadDashboardData();
            if (this.state.activeTab === 'folders') {
                await this.loadFolderContext(this.state.currentFolder ? this.state.currentFolder.id : false);
            }
            this.notification.add('Document moved', { type: 'success' });
        } catch (error) {
            console.error('Move failed', error);
            const msg = error.data?.message || error.message || 'Unknown error';
            this.notification.add('Failed to move document: ' + msg, { type: 'danger' });
        }
    }

    // Drag and drop documents into folders
    onDocDragStart(docId, ev) {
        ev.dataTransfer?.setData('text/plain', String(docId));
        this.state.draggingDocId = docId;
    }

    onDocDragEnd() {
        this.state.draggingDocId = null;
    }

    onFolderDragOver(ev) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = 'move';
    }

    async onFolderDrop(folderId, ev) {
        ev.preventDefault();
        const docId = this.state.draggingDocId || parseInt(ev.dataTransfer.getData('text/plain'), 10);
        if (!docId) return;
        await this.moveDocumentToFolder(docId, folderId);
        this.state.draggingDocId = null;
    }

    // Drag and Drop Upload
    onDragOver(event) {
        event.preventDefault();
        event.stopPropagation();
        this.state.dragOver = true;
    }

    onDragLeave(event) {
        event.preventDefault();
        event.stopPropagation();
        this.state.dragOver = false;
    }

    async onDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        this.state.dragOver = false;
        
        const files = event.dataTransfer.files;
        if (files.length === 0) return;
        
        for (const file of files) {
            await this.uploadFile(file);
        }
    }

    async uploadFile(file) {
        // Comprehensive list of supported file types (matching OnlyOffice capabilities)
        const allowedTypes = [
            // Word formats
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.template',
            'application/msword',
            'application/vnd.oasis.opendocument.text',
            'application/vnd.oasis.opendocument.text-template',
            'application/vnd.ms-word.document.macroenabled.12',
            'application/vnd.ms-word.template.macroenabled.12',
            'application/rtf',
            'text/rtf',
            'application/epub+zip',
            'text/html',
            // Excel formats
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.template',
            'application/vnd.ms-excel',
            'application/vnd.oasis.opendocument.spreadsheet',
            'application/vnd.oasis.opendocument.spreadsheet-template',
            'application/vnd.ms-excel.sheet.macroenabled.12',
            'application/vnd.ms-excel.sheet.binary.macroenabled.12',
            'application/vnd.ms-excel.template.macroenabled.12',
            'text/csv',
            'application/csv',
            // PowerPoint formats
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.openxmlformats-officedocument.presentationml.template',
            'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
            'application/vnd.ms-powerpoint',
            'application/vnd.oasis.opendocument.presentation',
            'application/vnd.oasis.opendocument.presentation-template',
            'application/vnd.ms-powerpoint.presentation.macroenabled.12',
            'application/vnd.ms-powerpoint.slideshow.macroenabled.12',
            'application/vnd.ms-powerpoint.template.macroenabled.12',
            // PDF formats
            'application/pdf',
            'application/acrobat',
            'application/x-pdf',
            // Text formats
            'text/plain',
            'text/markdown',
        ];
        
        if (!allowedTypes.includes(file.type)) {
            this.notification.add(`File type not supported: ${file.name} (${file.type})`, { type: "warning" });
            return;
        }
        
        try {
            this.notification.add(`Uploading ${file.name}...`, { type: "info" });
            
            const reader = new FileReader();
            reader.onload = async (e) => {
                const base64Data = e.target.result.split(',')[1];
                
                await this.orm.call("office.document", "upload_document", [
                    file.name,
                    base64Data,
                    this.state.currentFolder?.id || false,
                ]);
                
                this.notification.add(`${file.name} uploaded successfully!`, { type: "success" });
                await this.loadDashboardData();
            };
            reader.readAsDataURL(file);
            
        } catch (error) {
            console.error("Error uploading file:", error);
            this.notification.add(`Failed to upload ${file.name}`, { type: "danger" });
        }
    }

    onFileInputChange(event) {
        const files = event.target.files;
        for (const file of files) {
            this.uploadFile(file);
        }
        event.target.value = '';
    }

    triggerFileUpload() {
        if (this.fileInput && this.fileInput.el) {
            this.fileInput.el.click();
        }
    }

    openFolder(folderId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'office.document',
            view_mode: 'kanban,list,form',
            domain: [['folder_id', '=', folderId], ['is_trashed', '=', false]],
            context: { default_folder_id: folderId },
            name: 'Folder Documents',
        });
    }

    openMyDocuments() {
        this.action.doAction('office_document_creator.action_office_document');
    }

    openStarred() {
        this.action.doAction('office_document_creator.action_office_document_starred');
    }

    openShared() {
        this.action.doAction('office_document_creator.action_office_document_shared');
    }

    openTrash() {
        this.action.doAction('office_document_creator.action_office_document_trash');
    }

    openFolders() {
        this.setActiveTab('folders');
        this.openFolderModal(this.state.currentFolder ? this.state.currentFolder.id : null);
    }

    // Move modal
    openMoveModal(docId, ev) {
        ev && ev.stopPropagation();
        this.state.moveModal.visible = true;
        this.state.moveModal.docId = docId;
        this.state.moveModal.targetFolderId = this.state.currentFolder ? this.state.currentFolder.id : null;
    }

    closeMoveModal() {
        this.state.moveModal.visible = false;
        this.state.moveModal.docId = null;
        this.state.moveModal.targetFolderId = null;
    }

    async submitMove() {
        const { docId, targetFolderId } = this.state.moveModal;
        if (!docId) return;
        await this.moveDocumentToFolder(docId, targetFolderId || false);
        this.closeMoveModal();
    }

    // Share link modal
    async openShareLinkModal(docId, ev) {
        ev && ev.stopPropagation();
        try {
            const info = await this.orm.call('office.document', 'get_share_link_info', [[docId]]);
            this.state.shareModal = {
                visible: true,
                docId,
                url: info.url || '',
                permission: info.permission || 'view',
                active: info.active,
            };
        } catch (error) {
            console.error('Failed to load share link info', error);
            this.notification.add('Unable to load share link info', { type: 'danger' });
        }
    }

    closeShareModal() {
        this.state.shareModal.visible = false;
        this.state.shareModal.docId = null;
    }

    async saveShareLink() {
        const { docId, permission, active } = this.state.shareModal;
        if (!docId) return;
        try {
            const info = await this.orm.call('office.document', 'update_share_link', [[docId], permission, active, false]);
            this.state.shareModal.url = info.url || '';
            this.state.shareModal.permission = info.permission;
            this.state.shareModal.active = info.active;
            this.notification.add('Link settings saved', { type: 'success' });
        } catch (error) {
            console.error('Failed to save share link', error);
            const msg = error.data?.message || error.message || 'Unknown error';
            this.notification.add('Failed to save link: ' + msg, { type: 'danger' });
        }
    }

    copyShareLink() {
        if (!this.state.shareModal.url) return;
        navigator.clipboard?.writeText(this.state.shareModal.url);
        this.notification.add('Link copied to clipboard', { type: 'success' });
    }
}

OfficeDashboard.template = "office_document_creator.OfficeDashboard";

registry.category("actions").add("office_dashboard", OfficeDashboard);

// Keep the old widget for backwards compatibility
export class OfficeCreateWidget extends OfficeDashboard {}
OfficeCreateWidget.template = "office_document_creator.OfficeDashboard";
registry.category("actions").add("office_create_widget", OfficeCreateWidget);
