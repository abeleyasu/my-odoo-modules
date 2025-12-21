/** @odoo-module **/
/**
 * Office Drive - Enterprise Dashboard
 * 
 * Google Drive-like UI with:
 * - All file types support (16+ categories)
 * - Monaco Editor for code files
 * - Image/Video/Audio preview
 * - PDF.js viewer
 * - Folder upload & sharing
 * - Public share links with visible access list
 * - Chunked upload for large files (up to 10GB)
 * 
 * @copyright 2025 Odoo Community
 * @license LGPL-3.0 or later
 */

import { Component, useState, onMounted, useRef, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS, loadCSS } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

// ============================================================================
// CONSTANTS
// ============================================================================

const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB
const MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024; // 10GB

const FILE_ICONS = {
    // Documents
    word: 'fa-file-word',
    excel: 'fa-file-excel',
    powerpoint: 'fa-file-powerpoint',
    pdf: 'fa-file-pdf',
    text: 'fa-file-alt',
    
    // Media
    image: 'fa-file-image',
    video: 'fa-file-video',
    audio: 'fa-file-audio',
    
    // Code
    code: 'fa-file-code',
    
    // Archives
    archive: 'fa-file-archive',
    
    // Other
    ebook: 'fa-book',
    font: 'fa-font',
    design: 'fa-palette',
    cad: 'fa-drafting-compass',
    executable: 'fa-cog',
    other: 'fa-file',
};

const FOLDER_COLORS = {
    gray: '#9E9E9E',
    red: '#F44336',
    pink: '#E91E63',
    purple: '#9C27B0',
    deep_purple: '#673AB7',
    indigo: '#3F51B5',
    blue: '#2196F3',
    light_blue: '#03A9F4',
    cyan: '#00BCD4',
    teal: '#009688',
    green: '#4CAF50',
    light_green: '#8BC34A',
    lime: '#CDDC39',
    yellow: '#FFEB3B',
    amber: '#FFC107',
    orange: '#FF9800',
    deep_orange: '#FF5722',
    brown: '#795548',
};

// ============================================================================
// MAIN DASHBOARD COMPONENT
// ============================================================================

class OfficeDashboard extends Component {
    static template = "office_document_creator.Dashboard";
    
    setup() {
        this.state = useState({
            // Navigation
            currentView: 'my-drive', // my-drive, shared, starred, recent, trash
            currentFolderId: false,
            folderPath: [],
            
            // Data
            documents: [],
            folders: [],
            folderTree: [],
            
            // UI State
            loading: true,
            searchQuery: '',
            viewMode: 'grid', // grid, list
            sortBy: 'name', // name, modified, size
            sortOrder: 'asc',
            
            // Selection
            selectedItems: [],
            lastSelected: null,
            
            // Modals
            showCreateModal: false,
            showShareModal: false,
            showPreviewModal: false,
            showUploadModal: false,
            showMoveModal: false,
            showRenameModal: false,
            showDeleteConfirm: false,
            showCreateFolderModal: false,
            showRenameFolderModal: false,
            
            // Modal Data
            newFolderName: '',
            renameFolderTarget: null,
            renameFolderName: '',
            
            // Move Modal
            moveTarget: null,
            moveTargetType: null, // 'document' or 'folder'
            moveFolderTree: [],
            moveSelectedFolderId: null,
            moveExpandedFolders: {},
            
            // Rename Document Modal
            renameDocumentTarget: null,
            renameDocumentName: '',
            
            // Preview
            previewDocument: null,
            previewType: null,
            
            // Share
            shareTarget: null,
            shareAccessList: [],
            shareLink: null,
            userSearchResults: [],
            selectedUserForShare: null,
            
            // Upload
            uploadProgress: 0,
            uploadingFiles: [],
            
            // Stats
            storageUsed: 0,
            storageTotal: 15 * 1024 * 1024 * 1024, // 15 GB default
        });
        
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        // Current user info available via session.uid and session.name
        
        this.fileInputRef = useRef("fileInput");
        this.folderInputRef = useRef("folderInput");
        this.monacoEditorRef = useRef("monacoEditor");
        this.userSearchInputRef = useRef("userSearchInput");
        this.sharePermissionSelectRef = useRef("sharePermissionSelect");
        this.monacoInstance = null;
        
        onMounted(async () => {
            await this.loadDashboardData();
            await this.loadFolderTree();
            this._setupKeyboardShortcuts();
            this._setupDragAndDrop();
        });
        
        onWillUnmount(() => {
            this._cleanupKeyboardShortcuts();
            this._cleanupDragAndDrop();
            if (this.monacoInstance) {
                this.monacoInstance.dispose();
            }
        });
    }
    
    // ========================================================================
    // DATA LOADING
    // ========================================================================
    
    async loadDashboardData(folderId = false) {
        this.state.loading = true;
        try {
            const result = await rpc('/office/api/dashboard', {
                folder_id: folderId,
            });
            
            this.state.documents = result.documents || [];
            this.state.folders = result.folders || [];
            this.state.currentFolderId = folderId;
            this.state.folderPath = result.breadcrumb || [];
            this.state.storageUsed = result.storage_used || 0;
            
        } catch (error) {
            this.notification.add(`Error loading data: ${error.message}`, {
                type: 'danger',
            });
        }
        this.state.loading = false;
    }
    
    async loadFolderTree() {
        try {
            this.state.folderTree = await rpc('/office/api/folder/tree');
        } catch (error) {
            console.error('Failed to load folder tree:', error);
        }
    }
    
    async refreshData() {
        await this.loadDashboardData(this.state.currentFolderId);
    }
    
    // ========================================================================
    // NAVIGATION
    // ========================================================================
    
    async navigateToFolder(folderId) {
        await this.loadDashboardData(folderId);
        this.state.selectedItems = [];
    }
    
    async navigateToView(view) {
        this.state.currentView = view;
        this.state.currentFolderId = false;
        this.state.selectedItems = [];
        
        let result;
        switch (view) {
            case 'my-drive':
                await this.loadDashboardData(false);
                break;
            case 'shared':
                result = await rpc('/office/api/dashboard', { filter: 'shared' });
                this.state.documents = result.documents || [];
                this.state.folders = result.folders || [];
                break;
            case 'starred':
                result = await rpc('/office/api/dashboard', { filter: 'starred' });
                this.state.documents = result.documents || [];
                this.state.folders = [];
                break;
            case 'recent':
                result = await rpc('/office/api/dashboard', { filter: 'recent' });
                this.state.documents = result.documents || [];
                this.state.folders = [];
                break;
            case 'trash':
                result = await rpc('/office/api/dashboard', { filter: 'trash' });
                this.state.documents = result.documents || [];
                this.state.folders = result.folders || [];
                break;
        }
    }
    
    navigateBreadcrumb(index) {
        if (index < 0) {
            this.navigateToFolder(false);
        } else {
            const folder = this.state.folderPath[index];
            this.navigateToFolder(folder.id);
        }
    }
    
    // ========================================================================
    // FILE UPLOAD
    // ========================================================================
    
    triggerFileUpload() {
        this.fileInputRef.el.click();
    }
    
    triggerFolderUpload() {
        this.folderInputRef.el.click();
    }
    
    async onFileSelected(event) {
        const files = event.target.files;
        if (!files || files.length === 0) return;
        
        for (const file of files) {
            await this.uploadFile(file);
        }
        
        event.target.value = '';
        await this.refreshData();
    }
    
    async onFolderSelected(event) {
        const files = event.target.files;
        if (!files || files.length === 0) return;
        
        await this.uploadFolderFiles(files);
        event.target.value = '';
        await this.refreshData();
    }
    
    async uploadFile(file) {
        if (file.size > MAX_FILE_SIZE) {
            this.notification.add(
                `File ${file.name} exceeds 10 GB limit`,
                { type: 'danger' }
            );
            return;
        }
        
        if (file.size > CHUNK_SIZE) {
            // Use chunked upload for large files
            await this.chunkedUpload(file);
        } else {
            // Direct upload for small files
            await this.directUpload(file);
        }
    }
    
    async directUpload(file) {
        const uploadInfo = {
            name: file.name,
            progress: 0,
            status: 'uploading',
        };
        this.state.uploadingFiles.push(uploadInfo);
        
        try {
            const base64 = await this._readFileAsBase64(file);
            
            await this.orm.call('office.document', 'upload_document', [
                file.name,
                base64,
                this.state.currentFolderId,
            ]);
            
            uploadInfo.status = 'complete';
            uploadInfo.progress = 100;
            
            this.notification.add(`Uploaded ${file.name}`, { type: 'success' });
            
        } catch (error) {
            uploadInfo.status = 'error';
            this.notification.add(`Failed to upload ${file.name}`, { type: 'danger' });
        }
        
        // Remove from list after delay
        setTimeout(() => {
            const idx = this.state.uploadingFiles.indexOf(uploadInfo);
            if (idx >= 0) {
                this.state.uploadingFiles.splice(idx, 1);
            }
        }, 3000);
    }
    
    async chunkedUpload(file) {
        const uploadInfo = {
            name: file.name,
            progress: 0,
            status: 'uploading',
        };
        this.state.uploadingFiles.push(uploadInfo);
        
        try {
            // Initialize upload
            const initResult = await rpc('/office/upload/init', {
                filename: file.name,
                file_size: file.size,
                folder_id: this.state.currentFolderId,
            });
            
            const { upload_id, total_chunks } = initResult;
            
            // Upload chunks
            for (let i = 0; i < total_chunks; i++) {
                const start = i * CHUNK_SIZE;
                const end = Math.min(start + CHUNK_SIZE, file.size);
                const chunk = file.slice(start, end);
                const chunkBase64 = await this._readFileAsBase64(chunk);
                
                const formData = new FormData();
                formData.append('upload_id', upload_id);
                formData.append('chunk_index', i);
                formData.append('chunk_data', chunkBase64);
                
                await fetch('/office/upload/chunk', {
                    method: 'POST',
                    body: formData,
                });
                
                uploadInfo.progress = ((i + 1) / total_chunks) * 100;
            }
            
            // Complete upload
            await rpc('/office/upload/complete', {
                upload_id: upload_id,
            });
            
            uploadInfo.status = 'complete';
            this.notification.add(`Uploaded ${file.name}`, { type: 'success' });
            
        } catch (error) {
            uploadInfo.status = 'error';
            this.notification.add(`Failed to upload ${file.name}: ${error.message}`, { type: 'danger' });
        }
        
        setTimeout(() => {
            const idx = this.state.uploadingFiles.indexOf(uploadInfo);
            if (idx >= 0) {
                this.state.uploadingFiles.splice(idx, 1);
            }
        }, 3000);
    }
    
    async uploadFolderFiles(files) {
        // Group by folder structure
        const folderMap = {};
        let rootFolderName = '';
        
        for (const file of files) {
            const path = file.webkitRelativePath || file.name;
            const parts = path.split('/');
            
            if (!rootFolderName && parts.length > 1) {
                rootFolderName = parts[0];
            }
            
            folderMap[path] = file;
        }
        
        // Prepare file data
        const fileDataList = [];
        for (const [path, file] of Object.entries(folderMap)) {
            const base64 = await this._readFileAsBase64(file);
            fileDataList.push({
                path: path,
                name: file.name,
                data: base64,
            });
        }
        
        // Upload folder structure
        await rpc('/office/upload/folder', {
            folder_name: rootFolderName || 'Uploaded Folder',
            files: fileDataList,
            parent_folder_id: this.state.currentFolderId,
        });
        
        this.notification.add(`Uploaded folder "${rootFolderName}"`, { type: 'success' });
    }
    
    _readFileAsBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                const base64 = reader.result.split(',')[1];
                resolve(base64);
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }
    
    // ========================================================================
    // DOCUMENT ACTIONS
    // ========================================================================
    
    async openDocument(doc) {
        if (doc.preview_type === 'office') {
            // Open in OnlyOffice
            window.open(`/onlyoffice/editor/${doc.attachment_id}`, '_blank');
        } else if (['image', 'video', 'audio', 'pdf', 'code', 'text'].includes(doc.preview_type)) {
            // Open in preview modal
            this.state.previewDocument = doc;
            this.state.previewType = doc.preview_type;
            this.state.showPreviewModal = true;
            
            if (doc.preview_type === 'code') {
                await this._initMonacoEditor(doc);
            }
        } else {
            // Download
            window.open(`/office/download/${doc.id}`, '_blank');
        }
    }
    
    async _initMonacoEditor(doc) {
        // Load Monaco Editor from CDN
        if (!window.monaco) {
            await loadJS('https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs/loader.min.js');
            
            return new Promise((resolve) => {
                window.require.config({
                    paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' }
                });
                
                window.require(['vs/editor/editor.main'], () => {
                    this._createMonacoEditor(doc);
                    resolve();
                });
            });
        } else {
            this._createMonacoEditor(doc);
        }
    }
    
    _createMonacoEditor(doc) {
        setTimeout(() => {
            const container = this.monacoEditorRef.el;
            if (!container) return;
            
            if (this.monacoInstance) {
                this.monacoInstance.dispose();
            }
            
            this.monacoInstance = window.monaco.editor.create(container, {
                value: doc.content || '',
                language: doc.code_language || 'plaintext',
                theme: 'vs-dark',
                readOnly: false,
                automaticLayout: true,
                minimap: { enabled: true },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                formatOnPaste: true,
                formatOnType: true,
            });
        }, 100);
    }
    
    async saveCodeFile() {
        if (!this.monacoInstance || !this.state.previewDocument) return;
        
        const content = this.monacoInstance.getValue();
        
        await this.orm.call('office.document', 'save_content', [
            this.state.previewDocument.id,
            content,
        ]);
        
        this.notification.add('File saved', { type: 'success' });
    }
    
    closePreviewModal() {
        this.state.showPreviewModal = false;
        this.state.previewDocument = null;
        this.state.previewType = null;
        
        if (this.monacoInstance) {
            this.monacoInstance.dispose();
            this.monacoInstance = null;
        }
    }
    
    async createDocument(type) {
        this.state.showCreateModal = false;
        
        try {
            const result = await rpc('/office/api/document/create', {
                doc_type: type,
                folder_id: this.state.currentFolderId,
            });
            
            await this.refreshData();
            
            // Open in editor
            if (result.attachment_id) {
                window.open(`/onlyoffice/editor/${result.attachment_id}`, '_blank');
            }
            
        } catch (error) {
            this.notification.add(`Error creating document: ${error.message}`, { type: 'danger' });
        }
    }
    
    async createFolder() {
        this.state.showCreateFolderModal = true;
        this.state.newFolderName = '';
    }
    
    async confirmCreateFolder() {
        const name = this.state.newFolderName.trim();
        if (!name) {
            this.notification.add('Please enter a folder name', { type: 'warning' });
            return;
        }
        
        try {
            await rpc('/office/api/folder/create', {
                name: name,
                parent_id: this.state.currentFolderId,
            });
            
            this.state.showCreateFolderModal = false;
            await this.refreshData();
            await this.loadFolderTree();
            this.notification.add('Folder created successfully', { type: 'success' });
            
        } catch (error) {
            this.notification.add(`Error creating folder: ${error.message}`, { type: 'danger' });
        }
    }
    
    closeCreateFolderModal() {
        this.state.showCreateFolderModal = false;
        this.state.newFolderName = '';
    }
    
    // ========================================================================
    // DOCUMENT ACTIONS
    // ========================================================================
    
    async toggleDocumentStar(doc) {
        try {
            await rpc('/office/api/document/star', {
                document_id: doc.id,
            });
            await this.refreshData();
        } catch (error) {
            this.notification.add('Failed to update star', { type: 'danger' });
        }
    }
    
    async shareDocument(doc) {
        // Use proper Odoo wizard instead of custom modal
        this.action.doAction({
            name: `Share "${doc.name}"`,
            type: 'ir.actions.act_window',
            res_model: 'office.document.share.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: { default_document_id: doc.id },
        });
    }
    
    async downloadDocument(doc) {
        window.location.href = `/office/download/${doc.id}`;
    }
    
    async renameDocument(doc) {
        this.state.renameDocumentTarget = doc;
        this.state.renameDocumentName = doc.name;
        this.state.showRenameModal = true;
    }
    
    closeRenameDocumentModal() {
        this.state.showRenameModal = false;
        this.state.renameDocumentTarget = null;
        this.state.renameDocumentName = '';
    }
    
    async confirmRenameDocument() {
        if (!this.state.renameDocumentTarget || !this.state.renameDocumentName.trim()) return;
        
        const newName = this.state.renameDocumentName.trim();
        if (newName === this.state.renameDocumentTarget.name) {
            this.closeRenameDocumentModal();
            return;
        }
        
        try {
            await this.orm.write('office.document', [this.state.renameDocumentTarget.id], { name: newName });
            this.closeRenameDocumentModal();
            await this.refreshData();
            this.notification.add('Document renamed', { type: 'success' });
        } catch (error) {
            this.notification.add('Failed to rename document', { type: 'danger' });
        }
    }
    
    async openMoveModal(item, type) {
        // Open move modal for document or folder
        this.state.moveTarget = item;
        this.state.moveTargetType = type;
        this.state.moveSelectedFolderId = null;
        this.state.moveExpandedFolders = {};
        this.state.showMoveModal = true;
        
        // Load folder tree
        try {
            this.state.moveFolderTree = await this.orm.call(
                'office.folder', 'get_folder_tree', [false]
            );
        } catch (error) {
            console.error('Failed to load folder tree:', error);
            this.state.moveFolderTree = [];
        }
    }
    
    closeMoveModal() {
        this.state.showMoveModal = false;
        this.state.moveTarget = null;
        this.state.moveTargetType = null;
        this.state.moveFolderTree = [];
        this.state.moveSelectedFolderId = null;
    }
    
    selectMoveFolder(folderId) {
        this.state.moveSelectedFolderId = folderId;
    }
    
    toggleMoveFolder(folderId) {
        this.state.moveExpandedFolders = {
            ...this.state.moveExpandedFolders,
            [folderId]: !this.state.moveExpandedFolders[folderId]
        };
    }
    
    isMovefolderExpanded(folderId) {
        return this.state.moveExpandedFolders[folderId] || false;
    }
    
    async confirmMove() {
        if (!this.state.moveTarget) return;
        
        const targetFolderId = this.state.moveSelectedFolderId || false;
        
        try {
            if (this.state.moveTargetType === 'document') {
                await rpc('/office/api/document/move', {
                    document_id: this.state.moveTarget.id,
                    folder_id: targetFolderId,
                });
            } else if (this.state.moveTargetType === 'folder') {
                // Don't allow moving folder into itself or its children
                if (targetFolderId === this.state.moveTarget.id) {
                    this.notification.add('Cannot move folder into itself', { type: 'warning' });
                    return;
                }
                await rpc('/office/api/folder/move', {
                    folder_id: this.state.moveTarget.id,
                    target_parent_id: targetFolderId,
                });
            }
            
            this.closeMoveModal();
            await this.refreshData();
            this.notification.add('Moved successfully', { type: 'success' });
        } catch (error) {
            console.error('Move failed:', error);
            this.notification.add('Failed to move', { type: 'danger' });
        }
    }
    
    async moveDocument(doc) {
        this.openMoveModal(doc, 'document');
    }
    
    async moveFolder(folder) {
        this.openMoveModal(folder, 'folder');
    }
    
    async trashDocument(doc) {
        try {
            await rpc('/office/api/document/trash', {
                document_id: doc.id,
            });
            await this.refreshData();
            this.notification.add('Moved to trash', { type: 'success' });
        } catch (error) {
            this.notification.add('Failed to move to trash', { type: 'danger' });
        }
    }
    
    // ========================================================================
    // SELECTION
    // ========================================================================
    
    selectItem(item, event) {
        if (event.ctrlKey || event.metaKey) {
            // Toggle selection
            const idx = this.state.selectedItems.indexOf(item.id);
            if (idx >= 0) {
                this.state.selectedItems.splice(idx, 1);
            } else {
                this.state.selectedItems.push(item.id);
            }
        } else if (event.shiftKey && this.state.lastSelected) {
            // Range selection (simplified)
            this.state.selectedItems = [item.id];
        } else {
            // Single selection
            this.state.selectedItems = [item.id];
        }
        this.state.lastSelected = item.id;
    }
    
    // ========================================================================
    // DRAG AND DROP
    // ========================================================================
    
    onDragStart(event, item, type) {
        event.dataTransfer.setData('application/json', JSON.stringify({
            id: item.id,
            type: type, // 'document' or 'folder'
            name: item.name,
        }));
        event.dataTransfer.effectAllowed = 'move';
        // Add visual feedback
        event.target.classList.add('dragging');
    }
    
    onDragEnd(event) {
        event.target.classList.remove('dragging');
    }
    
    onDragOver(event) {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        event.currentTarget.classList.add('drag-over');
    }
    
    onDragLeave(event) {
        event.currentTarget.classList.remove('drag-over');
    }
    
    async onDropOnFolder(event, targetFolder) {
        event.preventDefault();
        event.currentTarget.classList.remove('drag-over');
        
        try {
            const data = JSON.parse(event.dataTransfer.getData('application/json'));
            
            // Don't drop folder into itself
            if (data.type === 'folder' && data.id === targetFolder.id) {
                return;
            }
            
            if (data.type === 'document') {
                await rpc('/office/api/document/move', {
                    document_id: data.id,
                    folder_id: targetFolder.id,
                });
            } else if (data.type === 'folder') {
                await rpc('/office/api/folder/move', {
                    folder_id: data.id,
                    target_parent_id: targetFolder.id,
                });
            }
            
            await this.refreshData();
            this.notification.add(`Moved "${data.name}" to "${targetFolder.name}"`, { type: 'success' });
        } catch (error) {
            console.error('Drop failed:', error);
            this.notification.add('Failed to move item', { type: 'danger' });
        }
    }
    
    async onDropOnRoot(event) {
        event.preventDefault();
        event.currentTarget.classList.remove('drag-over');
        
        try {
            const data = JSON.parse(event.dataTransfer.getData('application/json'));
            
            if (data.type === 'document') {
                await rpc('/office/api/document/move', {
                    document_id: data.id,
                    folder_id: false,
                });
            } else if (data.type === 'folder') {
                await rpc('/office/api/folder/move', {
                    folder_id: data.id,
                    target_parent_id: false,
                });
            }
            
            await this.refreshData();
            this.notification.add(`Moved "${data.name}" to My Drive`, { type: 'success' });
        } catch (error) {
            console.error('Drop failed:', error);
            this.notification.add('Failed to move item', { type: 'danger' });
        }
    }
    
    isSelected(itemId) {
        return this.state.selectedItems.includes(itemId);
    }
    
    clearSelection() {
        this.state.selectedItems = [];
    }
    
    selectAll() {
        const allIds = [
            ...this.state.folders.map(f => `folder_${f.id}`),
            ...this.state.documents.map(d => `doc_${d.id}`),
        ];
        this.state.selectedItems = allIds;
    }
    
    // ========================================================================
    // BULK ACTIONS
    // ========================================================================
    
    async deleteSelected() {
        if (this.state.selectedItems.length === 0) return;
        
        const itemCount = this.state.selectedItems.length;
        const selectedItems = [...this.state.selectedItems];
        
        this.dialog.add(ConfirmationDialog, {
            title: _t("Move to Trash"),
            body: _t("Move %s item(s) to trash?", itemCount),
            confirm: async () => {
                try {
                    for (const itemId of selectedItems) {
                        if (itemId.startsWith('doc_')) {
                            await rpc('/office/api/document/trash', {
                                document_id: parseInt(itemId.replace('doc_', '')),
                            });
                        } else if (itemId.startsWith('folder_')) {
                            await rpc('/office/api/folder/trash', {
                                folder_id: parseInt(itemId.replace('folder_', '')),
                            });
                        }
                    }
                    this.state.selectedItems = [];
                    await this.refreshData();
                    this.notification.add(_t("Moved to trash"), { type: 'success' });
                } catch (error) {
                    this.notification.add(_t("Failed to move items to trash"), { type: 'danger' });
                }
            },
            cancel: () => {},
        });
    }
    
    async starSelected() {
        for (const itemId of this.state.selectedItems) {
            if (itemId.startsWith('doc_')) {
                await rpc('/office/api/document/star', {
                    document_id: parseInt(itemId.replace('doc_', '')),
                });
            }
        }
        await this.refreshData();
    }
    
    // ========================================================================
    // SHARING
    // ========================================================================
    
    async openShareModal(item) {
        // Handle both folder and document items
        const targetType = item.is_folder || item.type === 'folder' ? 'folder' : 'document';
        const targetName = item.name || item.display_name || 'Item';
        
        this.state.shareTarget = { 
            type: targetType, 
            id: item.id, 
            name: targetName,
            is_folder: targetType === 'folder'
        };
        this.state.showShareModal = true;
        
        // Load share info using the new method
        await this.loadShareInfo(item.id, targetType);
    }
    
    closeShareModal() {
        this.state.showShareModal = false;
        this.state.shareTarget = null;
        this.state.shareAccessList = [];
        this.state.shareLink = null;
        this.state.userSearchResults = [];
        this.state.selectedUserForShare = null;
    }
    
    async addUserAccess(userId, permission) {
        const targetType = this.state.shareTarget.is_folder ? 'folder' : 'document';
        
        await rpc('/office/api/share/grant', {
            target_type: targetType,
            target_id: this.state.shareTarget.id,
            user_id: userId,
            permission: permission,
        });
        
        // Reload access list
        this.state.shareAccessList = await rpc('/office/api/share/access_list', {
            target_type: targetType,
            target_id: this.state.shareTarget.id,
        });
    }
    
    // ========================================================================
    // SEARCH
    // ========================================================================
    
    async onSearchInput(event) {
        this.state.searchQuery = event.target.value;
        
        if (this.searchDebounce) {
            clearTimeout(this.searchDebounce);
        }
        
        this.searchDebounce = setTimeout(async () => {
            if (this.state.searchQuery.length >= 2) {
                await this.orm.searchRead('res.users', [
                    ['share', '=', false],
                    ['id', '!=', this.env.session.uid],
                    '|',
                    ['name', 'ilike', this.state.searchQuery],
                    ['email', 'ilike', this.state.searchQuery],
                ], ['id', 'name', 'email', 'login'], { limit: 10 });
            } else if (this.state.searchQuery.length === 0) {
                await this.refreshData();
            }
        }, 300);
    }
    
    async performSearch() {
        const results = await rpc('/office/api/search', {
            query: this.state.searchQuery,
        });
        
        this.state.documents = results.documents || [];
        this.state.folders = results.folders || [];
    }
    
    // ========================================================================
    // VIEW & SORT
    // ========================================================================
    
    toggleViewMode() {
        this.state.viewMode = this.state.viewMode === 'grid' ? 'list' : 'grid';
    }
    
    setSortBy(field) {
        if (this.state.sortBy === field) {
            this.state.sortOrder = this.state.sortOrder === 'asc' ? 'desc' : 'asc';
        } else {
            this.state.sortBy = field;
            this.state.sortOrder = 'asc';
        }
        this._sortItems();
    }
    
    _sortItems() {
        const compare = (a, b) => {
            let aVal, bVal;
            
            switch (this.state.sortBy) {
                case 'name':
                    aVal = a.name.toLowerCase();
                    bVal = b.name.toLowerCase();
                    break;
                case 'modified':
                    aVal = new Date(a.write_date || a.create_date);
                    bVal = new Date(b.write_date || b.create_date);
                    break;
                case 'size':
                    aVal = a.file_size || 0;
                    bVal = b.file_size || 0;
                    break;
                default:
                    return 0;
            }
            
            let result = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
            return this.state.sortOrder === 'desc' ? -result : result;
        };
        
        this.state.folders.sort(compare);
        this.state.documents.sort(compare);
    }
    
    // ========================================================================
    // CONTEXT MENU
    // ========================================================================
    
    onContextMenu(event, item) {
        event.preventDefault();
        // Context menu is now handled by Bootstrap dropdown in template
    }
    
    // ========================================================================
    // FOLDER ACTIONS
    // ========================================================================
    
    async shareFolder(folder) {
        // Use proper Odoo wizard instead of custom modal
        this.action.doAction({
            name: `Share "${folder.name}"`,
            type: 'ir.actions.act_window',
            res_model: 'office.document.share.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: { default_folder_id: folder.id },
        });
    }
    
    async toggleFolderStar(folder) {
        try {
            await this.orm.call('office.folder', 'action_toggle_star', [[folder.id]]);
            await this.refreshData();
            this.notification.add(
                folder.is_starred ? 'Removed from starred' : 'Added to starred',
                { type: 'info' }
            );
        } catch (error) {
            this.notification.add('Failed to update star status', { type: 'danger' });
        }
    }
    
    async renameFolder(folder) {
        this.state.showRenameFolderModal = true;
        this.state.renameFolderTarget = folder;
        this.state.renameFolderName = folder.name;
    }
    
    async confirmRenameFolder() {
        const newName = this.state.renameFolderName.trim();
        if (!newName) {
            this.notification.add('Please enter a folder name', { type: 'warning' });
            return;
        }
        
        if (newName === this.state.renameFolderTarget.name) {
            this.state.showRenameFolderModal = false;
            return;
        }
        
        try {
            await this.orm.call('office.folder', 'action_rename', [[this.state.renameFolderTarget.id], newName]);
            this.state.showRenameFolderModal = false;
            await this.refreshData();
            this.notification.add('Folder renamed successfully', { type: 'success' });
        } catch (error) {
            this.notification.add('Failed to rename folder', { type: 'danger' });
        }
    }
    
    closeRenameFolderModal() {
        this.state.showRenameFolderModal = false;
        this.state.renameFolderTarget = null;
        this.state.renameFolderName = '';
    }
    
    async changeFolderColor(folder) {
        // Show color picker
        const colors = [
            '#F44336', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3',
            '#03A9F4', '#00BCD4', '#009688', '#4CAF50', '#8BC34A', '#CDDC39',
            '#FFEB3B', '#FFC107', '#FF9800', '#FF5722', '#795548', '#9E9E9E'
        ];
        
        // Create color picker dialog
        const colorHtml = colors.map(c => 
            `<button class="btn p-0 m-1" style="width:32px;height:32px;background:${c};border:2px solid ${c===folder.color?'#000':'transparent'};border-radius:4px;" data-color="${c}"></button>`
        ).join('');
        
        const dialog = document.createElement('div');
        dialog.innerHTML = `
            <div class="modal fade" tabindex="-1">
                <div class="modal-dialog modal-sm">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Choose Color</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center">${colorHtml}</div>
                    </div>
                </div>
            </div>`;
        document.body.appendChild(dialog);
        
        const modal = new bootstrap.Modal(dialog.querySelector('.modal'));
        modal.show();
        
        dialog.querySelectorAll('[data-color]').forEach(btn => {
            btn.onclick = async () => {
                const color = btn.dataset.color;
                try {
                    await this.orm.call('office.folder', 'action_set_color', [[folder.id], color]);
                    await this.refreshData();
                    modal.hide();
                    this.notification.add('Color updated', { type: 'success' });
                } catch (error) {
                    this.notification.add('Failed to update color', { type: 'danger' });
                }
            };
        });
        
        dialog.querySelector('.modal').addEventListener('hidden.bs.modal', () => {
            dialog.remove();
        });
    }
    
    async trashFolder(folder) {
        if (confirm(`Move "${folder.name}" to trash?`)) {
            try {
                await this.orm.call('office.folder', 'action_move_to_trash', [[folder.id]]);
                await this.refreshData();
                this.notification.add('Folder moved to trash', { type: 'success' });
            } catch (error) {
                this.notification.add('Failed to move folder to trash', { type: 'danger' });
            }
        }
    }
    
    // ========================================================================
    // SHARE MODAL METHODS
    // ========================================================================
    
    async loadShareInfo(targetId, targetType) {
        try {
            // Reset state
            this.state.shareAccessList = [];
            this.state.shareLink = null;
            this.state.userSearchResults = [];
            this.state.selectedUserForShare = null;
            
            // Use existing RPC endpoints
            this.state.shareAccessList = await rpc('/office/api/share/access_list', {
                target_type: targetType,
                target_id: targetId,
            });
            
            this.state.shareLink = await rpc('/office/api/share/link', {
                target_type: targetType,
                target_id: targetId,
            });
            
        } catch (error) {
            console.error('Failed to load share info:', error);
            this.notification.add('Failed to load sharing info', { type: 'danger' });
        }
    }
    
    async onUserSearchInput(event) {
        const query = event.target.value.trim();
        
        if (query.length < 2) {
            this.state.userSearchResults = [];
            return;
        }
        
        try {
            console.debug('[OfficeDashboard] onUserSearchInput query=', query);
            // Use dedicated user search endpoint for reliability
            const existingUserIds = this.state.shareAccessList.map(a => a.user_id);
            
            const users = await rpc('/office/api/users/search', {
                query: query,
                exclude_ids: existingUserIds,
                limit: 10,
            });
            
            console.debug('[OfficeDashboard] onUserSearchInput results=', users);
            this.state.userSearchResults = users || [];
            
        } catch (error) {
            console.error('User search failed:', error);
            this.state.userSearchResults = [];
        }
    }
    
    onUserSearchKeydown(event) {
        if (event.key === 'Enter' && this.state.userSearchResults.length > 0) {
            event.preventDefault();
            this.selectUserForSharing(this.state.userSearchResults[0]);
        } else if (event.key === 'Escape') {
            this.state.userSearchResults = [];
        }
    }
    
    selectUserForSharing(user) {
        console.debug('[OfficeDashboard] selectUserForSharing user=', user);
        this.state.selectedUserForShare = user;
        this.state.userSearchResults = [];
        // Update search input with user name using ref
        if (this.userSearchInputRef.el) {
            this.userSearchInputRef.el.value = user.name;
        }
    }
    
    async addSelectedUser() {
        const user = this.state.selectedUserForShare;
        console.debug('[OfficeDashboard] addSelectedUser selectedUserForShare=', user);
        if (!this.state.shareTarget) return;
        // Fallback: if user not selected from dropdown, try lookup by email/name directly
        let targetUser = user;
        if (!targetUser && this.userSearchInputRef.el) {
            const raw = this.userSearchInputRef.el.value.trim();
            if (raw) {
                try {
                    // Use dedicated user search endpoint
                    const existingUserIds = this.state.shareAccessList.map(a => a.user_id);
                    const found = await rpc('/office/api/users/search', {
                        query: raw,
                        exclude_ids: existingUserIds,
                        limit: 1,
                    });
                    targetUser = found && found.length ? found[0] : null;
                    if (!targetUser) {
                        this.notification.add(_t('No matching user found'), { type: 'warning' });
                        return;
                    }
                } catch (err) {
                    console.error('User lookup failed:', err);
                    this.notification.add(_t('User search failed'), { type: 'danger' });
                    return;
                }
            }
        }
        if (!targetUser) {
            this.notification.add(_t('Please select a user to share with'), { type: 'warning' });
            return;
        }
        
        try {
            // Get permission from the ref or fallback
            const permissionSelect = this.sharePermissionSelectRef.el;
            const permission = permissionSelect ? permissionSelect.value : 'viewer';
            
            const targetType = this.state.shareTarget.type;
            const targetId = this.state.shareTarget.id;
            
            // Use existing RPC endpoint
            await rpc('/office/api/share/grant', {
                target_type: targetType,
                target_id: targetId,
                user_id: targetUser.id,
                permission: permission,
            });
            
            // Clear selection and search input
            this.state.selectedUserForShare = null;
            this.state.userSearchResults = [];
            if (this.userSearchInputRef.el) {
                this.userSearchInputRef.el.value = '';
            }
            
            this.notification.add(`Shared with ${targetUser.name}`, { type: 'success' });
            
            // Reload share info
            await this.loadShareInfo(targetId, targetType);
            
        } catch (error) {
            console.error('Failed to share:', error);
            this.notification.add('Failed to share', { type: 'danger' });
        }
    }
    
    async updateUserAccess(userId, newPermission) {
        if (!this.state.shareTarget) return;
        
        try {
            const targetType = this.state.shareTarget.type;
            const targetId = this.state.shareTarget.id;
            
            await rpc('/office/api/share/grant', {
                target_type: targetType,
                target_id: targetId,
                user_id: userId,
                permission: newPermission,
            });
            
            this.notification.add('Permission updated', { type: 'success' });
            
            // Reload share info
            await this.loadShareInfo(targetId, targetType);
            
        } catch (error) {
            console.error('Failed to update permission:', error);
            this.notification.add('Failed to update permission', { type: 'danger' });
        }
    }
    
    async removeUserAccess(userId) {
        if (!this.state.shareTarget) return;
        
        if (!confirm('Remove access for this user?')) return;
        
        try {
            const targetType = this.state.shareTarget.type;
            const targetId = this.state.shareTarget.id;
            
            await rpc('/office/api/share/revoke', {
                target_type: targetType,
                target_id: targetId,
                user_id: userId,
            });
            
            this.notification.add('Access removed', { type: 'success' });
            
            // Reload share info
            await this.loadShareInfo(targetId, targetType);
            
        } catch (error) {
            console.error('Failed to remove access:', error);
            this.notification.add('Failed to remove access', { type: 'danger' });
        }
    }
    
    async toggleShareLink(enable) {
        if (!this.state.shareTarget) return;
        
        try {
            const targetType = this.state.shareTarget.type;
            const targetId = this.state.shareTarget.id;
            
            this.state.shareLink = await rpc('/office/api/share/link/update', {
                target_type: targetType,
                target_id: targetId,
                active: enable,
                permission: this.state.shareLink ? (this.state.shareLink.permission || 'viewer') : 'viewer',
                allow_download: this.state.shareLink ? this.state.shareLink.allow_download : true,
            });
            
            this.notification.add(
                enable ? 'Link sharing enabled' : 'Link sharing disabled',
                { type: 'success' }
            );
            
        } catch (error) {
            console.error('Failed to toggle link sharing:', error);
            this.notification.add('Failed to update link sharing', { type: 'danger' });
        }
    }
    
    copyShareLink() {
        if (!this.state.shareLink || !this.state.shareLink.url) return;
        
        navigator.clipboard.writeText(this.state.shareLink.url).then(() => {
            this.notification.add('Link copied to clipboard', { type: 'success' });
        }).catch(() => {
            this.notification.add('Failed to copy link', { type: 'danger' });
        });
    }
    
    async updateLinkPermission(permission) {
        if (!this.state.shareTarget || !this.state.shareLink) return;
        
        try {
            const targetType = this.state.shareTarget.type;
            const targetId = this.state.shareTarget.id;
            
            this.state.shareLink = await rpc('/office/api/share/link/update', {
                target_type: targetType,
                target_id: targetId,
                is_active: true,
                permission: permission,
                allow_download: this.state.shareLink.allow_download,
            });
            
            this.notification.add('Link permission updated', { type: 'success' });
        } catch (error) {
            console.error('Failed to update link permission:', error);
            this.notification.add('Failed to update link permission', { type: 'danger' });
        }
    }
    
    async updateLinkDownload(allowDownload) {
        if (!this.state.shareTarget || !this.state.shareLink) return;
        
        try {
            const targetType = this.state.shareTarget.type;
            const targetId = this.state.shareTarget.id;
            
            this.state.shareLink = await rpc('/office/api/share/link/update', {
                target_type: targetType,
                target_id: targetId,
                is_active: true,
                permission: this.state.shareLink.permission || 'viewer',
                allow_download: allowDownload,
            });
            
            this.notification.add(allowDownload ? 'Download enabled' : 'Download disabled', { type: 'success' });
        } catch (error) {
            console.error('Failed to update download setting:', error);
            this.notification.add('Failed to update download setting', { type: 'danger' });
        }
    }
    
    // ========================================================================
    // DRAG & DROP
    // ========================================================================
    
    _setupDragAndDrop() {
        this._onDrop = this.onDrop.bind(this);
        this._onDragOver = this.onDragOver.bind(this);
        
        document.addEventListener('drop', this._onDrop);
        document.addEventListener('dragover', this._onDragOver);
    }
    
    _cleanupDragAndDrop() {
        document.removeEventListener('drop', this._onDrop);
        document.removeEventListener('dragover', this._onDragOver);
    }
    
    onDragOver(event) {
        event.preventDefault();
    }
    
    async onDrop(event) {
        event.preventDefault();
        
        const files = event.dataTransfer && event.dataTransfer.files;
        if (!files || files.length === 0) return;
        
        for (const file of files) {
            await this.uploadFile(file);
        }
        
        await this.refreshData();
    }
    
    // ========================================================================
    // KEYBOARD SHORTCUTS
    // ========================================================================
    
    _setupKeyboardShortcuts() {
        this._onKeyDown = this.onKeyDown.bind(this);
        document.addEventListener('keydown', this._onKeyDown);
    }
    
    _cleanupKeyboardShortcuts() {
        document.removeEventListener('keydown', this._onKeyDown);
    }
    
    onKeyDown(event) {
        // Ignore if in input/textarea
        if (['INPUT', 'TEXTAREA'].includes(event.target.tagName)) return;
        
        if (event.ctrlKey || event.metaKey) {
            switch (event.key) {
                case 'a':
                    event.preventDefault();
                    this.selectAll();
                    break;
                case 'u':
                    event.preventDefault();
                    this.triggerFileUpload();
                    break;
                case 'f':
                    event.preventDefault();
                    const searchInput = document.getElementById('office-search-input');
                    if (searchInput) searchInput.focus();
                    break;
            }
        } else {
            switch (event.key) {
                case 'Delete':
                    if (this.state.selectedItems.length > 0) {
                        this.deleteSelected();
                    }
                    break;
                case 'Escape':
                    this.clearSelection();
                    this.closePreviewModal();
                    this.closeShareModal();
                    break;
                case 'Enter':
                    if (this.state.selectedItems.length === 1) {
                        const itemId = this.state.selectedItems[0];
                        if (itemId.startsWith('folder_')) {
                            const folderId = parseInt(itemId.replace('folder_', ''));
                            this.navigateToFolder(folderId);
                        } else {
                            const docId = parseInt(itemId.replace('doc_', ''));
                            const doc = this.state.documents.find(d => d.id === docId);
                            if (doc) this.openDocument(doc);
                        }
                    }
                    break;
            }
        }
    }
    
    // ========================================================================
    // UTILITIES
    // ========================================================================
    
    getFileIcon(doc) {
        return FILE_ICONS[doc.file_category] || FILE_ICONS.other;
    }
    
    getFileTypeClass(doc) {
        // Return colorful CSS class based on file category
        const categoryMap = {
            'word': 'file-word',
            'excel': 'file-excel',
            'powerpoint': 'file-powerpoint',
            'pdf': 'file-pdf',
            'text': 'file-text',
            'image': 'file-image',
            'video': 'file-video',
            'audio': 'file-audio',
            'code': 'file-code',
            'archive': 'file-archive',
            'ebook': 'file-ebook',
            'font': 'file-font',
            'design': 'file-design',
            'cad': 'file-cad',
            'executable': 'file-executable',
        };
        
        // Special handling for code files with language-specific colors
        if (doc.file_category === 'code') {
            const ext = doc.name.split('.').pop().toLowerCase();
            const codeMap = {
                'js': 'file-code-js',
                'jsx': 'file-code-js',
                'ts': 'file-code-js',
                'tsx': 'file-code-js',
                'py': 'file-code-python',
                'java': 'file-code-java',
                'cpp': 'file-code-cpp',
                'c': 'file-code-cpp',
                'html': 'file-code-html',
                'htm': 'file-code-html',
                'css': 'file-code-css',
                'scss': 'file-code-css',
            };
            if (codeMap[ext]) return codeMap[ext];
        }
        
        return categoryMap[doc.file_category] || 'file-other';
    }
    
    formatFileSize(bytes) {
        if (!bytes) return '-';
        
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let unitIndex = 0;
        let size = bytes;
        
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        
        return `${size.toFixed(1)} ${units[unitIndex]}`;
    }
    
    formatTimeAgo(dateString) {
        if (!dateString) return '';
        
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        
        if (seconds < 60) return 'Just now';
        if (seconds < 3600) return Math.floor(seconds / 60) + ' minutes ago';
        if (seconds < 86400) return Math.floor(seconds / 3600) + ' hours ago';
        if (seconds < 172800) return 'Yesterday';
        if (seconds < 604800) return Math.floor(seconds / 86400) + ' days ago';
        
        // Format as date if older than a week
        const options = { month: 'short', day: 'numeric', year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined };
        return date.toLocaleDateString('en-US', options);
    }
    
    formatDate(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)} min ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
        if (diff < 604800000) return `${Math.floor(diff / 86400000)} days ago`;
        
        return date.toLocaleDateString();
    }
    
    get storagePercentage() {
        return (this.state.storageUsed / this.state.storageTotal) * 100;
    }
    
    get storageUsedFormatted() {
        return this.formatFileSize(this.state.storageUsed);
    }
    
    get storageTotalFormatted() {
        return this.formatFileSize(this.state.storageTotal);
    }
}

OfficeDashboard.template = "office_document_creator.Dashboard";

// ============================================================================
// REGISTRY
// ============================================================================

registry.category("actions").add("office_dashboard", OfficeDashboard);

export { OfficeDashboard };
