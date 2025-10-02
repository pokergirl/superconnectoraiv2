'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { getAccessRequests, approveAccessRequest, denyAccessRequest } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { useToast } from '@/hooks/use-toast';
import { Copy, Check } from 'lucide-react';

interface AccessRequest {
  id: string;
  email: string;
  full_name: string;
  reason?: string;
  organization?: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  processed_at?: string;
}

export default function AccessRequestsPage() {
  const { token } = useAuth();
  const { toast } = useToast();
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [processingId, setProcessingId] = useState<string | null>(null);
  const fetchRequests = async () => {
    if (!token) return;
    
    try {
      setLoading(true);
      const filter = statusFilter === 'all' ? undefined : statusFilter;
      const data = await getAccessRequests(token, filter);
      setRequests(data as AccessRequest[]);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch access requests",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, [token, statusFilter]);

  const handleApprove = async (requestId: string) => {
    if (!token) return;
    
    try {
      setProcessingId(requestId);
      const response = await approveAccessRequest(requestId, token);
      
      // Open email client with pre-drafted approval email
      if (response.email_template) {
        const { to, subject, body } = response.email_template;
        const mailtoLink = `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
        window.open(mailtoLink, '_blank');
        
        toast({
          title: "Request Approved",
          description: "User created successfully. Your email client should open with a pre-drafted approval email.",
        });
      } else {
        toast({
          title: "Request Approved",
          description: "User created successfully, but email template was not generated.",
        });
      }
      
      // Refresh the list
      await fetchRequests();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to approve request",
        variant: "destructive",
      });
    } finally {
      setProcessingId(null);
    }
  };

  const handleDeny = async (request: AccessRequest) => {
    if (!token) return;
    
    try {
      setProcessingId(request.id);
      const response = await denyAccessRequest(request.id, token, ''); // Empty reason since we're removing the modal
      
      // Open email client with pre-drafted denial email
      if (response.email_template) {
        const { to, subject, body } = response.email_template;
        const mailtoLink = `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
        window.open(mailtoLink, '_blank');
        
        toast({
          title: "Request Denied",
          description: "Access request denied successfully. Your email client should open with a pre-drafted denial email.",
        });
      } else {
        toast({
          title: "Request Denied",
          description: "Access request denied successfully, but email template was not generated.",
        });
      }
      
      // Refresh the list
      await fetchRequests();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to deny request",
        variant: "destructive",
      });
    } finally {
      setProcessingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">Pending</Badge>;
      case 'approved':
        return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">Approved</Badge>;
      case 'rejected':
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">Rejected</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-lg">Loading access requests...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Access Requests</h1>
          <p className="text-gray-600 mt-2">Manage user access requests to the platform</p>
        </div>
        <div className="flex items-center gap-4">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Requests</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {requests.length === 0 ? (
        <Card>
          <CardContent className="flex items-center justify-center h-64">
            <div className="text-center">
              <p className="text-lg text-gray-500">No access requests found</p>
              <p className="text-sm text-gray-400 mt-2">
                {statusFilter !== 'all' ? `No ${statusFilter} requests` : 'No requests have been submitted yet'}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {requests.map((request) => (
            <Card key={request.id}>
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg">{request.full_name}</CardTitle>
                    <CardDescription>{request.email}</CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusBadge(request.status)}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4">
                  {request.organization && (
                    <div>
                      <Label className="text-sm font-medium text-gray-700">Organization</Label>
                      <p className="text-sm text-gray-600">{request.organization}</p>
                    </div>
                  )}
                  {request.reason && (
                    <div>
                      <Label className="text-sm font-medium text-gray-700">Reason for Access</Label>
                      <p className="text-sm text-gray-600">{request.reason}</p>
                    </div>
                  )}
                  <div className="flex justify-between items-center text-xs text-gray-500">
                    <span>Submitted: {formatDate(request.created_at)}</span>
                    {request.processed_at && (
                      <span>Processed: {formatDate(request.processed_at)}</span>
                    )}
                  </div>
                  {request.status === 'pending' && (
                    <div className="flex gap-2 pt-4 border-t">
                      <Button
                        onClick={() => handleApprove(request.id)}
                        disabled={processingId === request.id}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        {processingId === request.id ? 'Approving...' : 'Approve'}
                      </Button>
                      <Button
                        onClick={() => handleDeny(request)}
                        disabled={processingId === request.id}
                        variant="destructive"
                      >
                        {processingId === request.id ? 'Denying...' : 'Deny'}
                      </Button>
                    </div>
                  )}
                  <p className="text-xs text-gray-500 mt-2">
                    📧 Your email client will open with a pre-drafted email to send to the user
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}


    </div>
  );
}