'use client';

import { useState } from 'react';
import { useAuth } from '../../../src/context/AuthContext';
import { Button } from '../../../src/components/ui/button';
import { Input } from '../../../src/components/ui/input';
import { Label } from '../../../src/components/ui/label';
import { uploadConnectionsCSV, deleteConnections, clearPineconeData } from '../../../src/lib/api';

export default function DataManagementPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [message, setMessage] = useState('');
  const { token } = useAuth();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file || !token) return;
    setUploading(true);
    setMessage('');
    try {
      const response = await uploadConnectionsCSV(file);
      setMessage(response.message);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async () => {
    if (!token) return;
    if (!confirm('Are you sure you want to delete all your connections? This action cannot be undone.')) return;
    setDeleting(true);
    setMessage('');
    try {
      await deleteConnections(token);
      setMessage('All connections deleted successfully.');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Deletion failed');
    } finally {
      setDeleting(false);
    }
  };

  const handleClearPinecone = async () => {
    if (!token) return;
    if (!confirm('Are you sure you want to clear your Pinecone data? This will remove all embeddings.')) return;
    setClearing(true);
    setMessage('');
    try {
      const response = await clearPineconeData(token);
      setMessage(response.message);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to clear Pinecone data');
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Upload Connections</h1>
      
      <div className="space-y-8">
        {/* Upload Connections */}
        <div className="p-6 border rounded-lg">
          <h2 className="text-xl font-semibold mb-4">Upload Connections</h2>
          <div className="flex items-center space-x-4">
            <Label htmlFor="csv-upload" className="cursor-pointer">
              <Input id="csv-upload" type="file" accept=".csv" onChange={handleFileChange} className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"/>
            </Label>
            <Button onClick={handleUpload} disabled={!file || uploading}>
              {uploading ? 'Uploading...' : 'Upload CSV'}
            </Button>
          </div>
        </div>

        {/* Delete Connections */}
        <div className="p-6 border rounded-lg">
          <h2 className="text-xl font-semibold mb-4">Delete All Connections</h2>
          <p className="text-gray-600 mb-4">This will permanently delete all your connection data from the database.</p>
          <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
            {deleting ? 'Deleting...' : 'Delete All Connections'}
          </Button>
        </div>

        {/* Clear Pinecone Data */}
        <div className="p-6 border rounded-lg">
          <h2 className="text-xl font-semibold mb-4">Clear Pinecone Index</h2>
          <p className="text-gray-600 mb-4">This will remove all your data from the Pinecone search index. You will need to re-upload your connections to use the search feature.</p>
          <Button variant="destructive" onClick={handleClearPinecone} disabled={clearing}>
            {clearing ? 'Clearing...' : 'Clear Pinecone Data'}
          </Button>
        </div>
      </div>

      {message && <p className="mt-6 text-center">{message}</p>}
    </div>
  );
}