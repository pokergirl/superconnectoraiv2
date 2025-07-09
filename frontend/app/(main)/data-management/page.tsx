'use client';

import { useState } from 'react';
import { useAuth } from '../../../src/context/AuthContext';
import { uploadConnectionsCSV, deleteConnections } from '../../../src/lib/api';
import { Button } from "../../../src/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "../../../src/components/ui/card";
import { Input } from "../../../src/components/ui/input";
import { Label } from "../../../src/components/ui/label";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "../../../src/components/ui/alert-dialog";

export default function DataManagementPage() {
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { token } = useAuth();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file || !token) return;
    setLoading(true);
    setMessage('');
    setError('');
    try {
      const result = await uploadConnectionsCSV(file, token);
      setMessage(result.message);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!token) return;
    setLoading(true);
    setMessage('');
    setError('');
    try {
      await deleteConnections(token);
      setMessage('Successfully deleted all connections.');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Data Management</h1>
      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Upload Connections</CardTitle>
            <CardDescription>Upload a CSV file of your LinkedIn connections. This will replace your existing dataset.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2">
              <Label htmlFor="csv-file">CSV File</Label>
              <Input id="csv-file" type="file" accept=".csv" onChange={handleFileChange} />
            </div>
          </CardContent>
          <CardFooter>
            <Button onClick={handleUpload} disabled={!file || loading}>
              {loading ? 'Uploading...' : 'Upload and Replace'}
            </Button>
          </CardFooter>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Delete Dataset</CardTitle>
            <CardDescription>Permanently delete your entire connections dataset. This action cannot be undone.</CardDescription>
          </CardHeader>
          <CardFooter>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" disabled={loading}>Delete All Connections</Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will permanently delete your entire connection dataset. This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={handleDelete}>Continue</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </CardFooter>
        </Card>
        {message && <p className="text-green-600">{message}</p>}
        {error && <p className="text-red-600">{error}</p>}
      </div>
    </div>
  );
}