'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { getWarmIntroRequests, updateWarmIntroRequestStatus, exportConnectedRequestsCSV } from '@/lib/api';
import { WarmIntroRequest, WarmIntroStatus, PaginatedWarmIntroRequests } from '@/lib/types';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { ChevronLeft, ChevronRight, Filter, RefreshCw, Download } from "lucide-react";
import { cn } from "@/lib/utils";
import { telemetry } from '@/lib/telemetry';
import DatePickerModal from '@/components/shared/DatePickerModal';

export default function WarmIntroRequestsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const [requests, setRequests] = useState<WarmIntroRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [totalPages, setTotalPages] = useState(1);
  const [totalRequests, setTotalRequests] = useState(0);
  const [statusCounts, setStatusCounts] = useState({
    total: 0,
    pending: 0,
    connected: 0,
    declined: 0
  });
  const [updatingStatus, setUpdatingStatus] = useState<string | null>(null);
  const [pageLoadTime] = useState<number>(Date.now());
  const [exportingCSV, setExportingCSV] = useState(false);
  const [datePickerModal, setDatePickerModal] = useState<{
    isOpen: boolean;
    requestId: string;
    status: WarmIntroStatus;
    title: string;
    description: string;
  }>({
    isOpen: false,
    requestId: '',
    status: WarmIntroStatus.pending,
    title: '',
    description: ''
  });
  const { token } = useAuth();
  const { toast } = useToast();

  // Get URL parameters
  const currentPage = parseInt(searchParams.get('page') || '1', 10);
  const statusFilter = (searchParams.get('status') || 'all') as 'all' | WarmIntroStatus;

  const limit = 10;

  // Function to update URL parameters
  const updateURL = (newPage?: number, newStatus?: string) => {
    const params = new URLSearchParams(searchParams);
    
    if (newPage !== undefined) {
      if (newPage === 1) {
        params.delete('page');
      } else {
        params.set('page', newPage.toString());
      }
    }
    
    if (newStatus !== undefined) {
      if (newStatus === 'all') {
        params.delete('status');
      } else {
        params.set('status', newStatus);
      }
    }
    
    const newURL = params.toString() ? `?${params.toString()}` : '';
    router.push(`/warm-intro-requests${newURL}`);
  };

  const fetchRequests = useCallback(async (page: number = currentPage, status: 'all' | WarmIntroStatus = statusFilter) => {
    if (!token) return;
    
    const startTime = Date.now();
    setLoading(true);
    try {
      const filterStatus = status === 'all' ? undefined : status;
      const response: PaginatedWarmIntroRequests = await getWarmIntroRequests(
        token,
        page,
        limit,
        filterStatus
      );
      
      setRequests(response.items);
      setTotalPages(response.total_pages);
      setTotalRequests(response.total);
      setStatusCounts(response.status_counts);
      
      // Track successful data load
      telemetry.track('api_request_performance', {
        endpoint: '/warm-intro-requests',
        method: 'GET',
        duration_ms: Date.now() - startTime,
        status_code: 200,
        success: true,
      });
      
      // Track page load analytics
      telemetry.track('requests_page_loaded', {
        total_requests: response.total,
        pending_count: response.items.filter(r => r.status === WarmIntroStatus.pending).length,
        connected_count: response.items.filter(r => r.status === WarmIntroStatus.connected).length,
        declined_count: response.items.filter(r => r.status === WarmIntroStatus.declined).length,
        current_page: page,
        status_filter: status,
      });
      
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
      
      // Track API error
      telemetry.track('api_request_performance', {
        endpoint: '/warm-intro-requests',
        method: 'GET',
        duration_ms: Date.now() - startTime,
        status_code: 500,
        success: false,
      });
      
      toast({
        title: "Error",
        description: "Failed to fetch warm intro requests",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [currentPage, statusFilter, token, toast]);

  useEffect(() => {
    fetchRequests(currentPage, statusFilter);
  }, [fetchRequests, currentPage, statusFilter]);

  // Track initial page load performance
  useEffect(() => {
    const loadTime = Date.now() - pageLoadTime;
    telemetry.track('page_load_performance', {
      page_name: 'warm_intro_requests',
      load_time_ms: loadTime,
      initial_data_load_ms: loadTime, // Will be updated when data loads
    });
  }, [pageLoadTime]);

  const handleStatusUpdate = async (requestId: string, newStatus: WarmIntroStatus, selectedDate?: string) => {
    if (!token) return;
    
    const request = requests.find(r => r.id === requestId);
    const previousStatus = request?.status;
    const startTime = Date.now();
    
    // Track status update initiation
    if (request) {
      telemetry.track('status_update_initiated', {
        request_id: requestId,
        previous_status: previousStatus || 'unknown',
        new_status: newStatus,
        requester_name: request.requester_name,
        connection_name: request.connection_name,
      });
    }
    
    setUpdatingStatus(requestId);
    try {
      const connectedDate = newStatus === WarmIntroStatus.connected ? selectedDate : undefined;
      const declinedDate = newStatus === WarmIntroStatus.declined ? selectedDate : undefined;
      
      await updateWarmIntroRequestStatus(requestId, newStatus, token, connectedDate, declinedDate);
      
      // Optimistically update the local state
      setRequests(prev => prev.map(req =>
        req.id === requestId
          ? {
              ...req,
              status: newStatus,
              updated_at: new Date().toISOString(),
              connected_date: connectedDate || null,
              declined_date: declinedDate || null
            }
          : req
      ));
      
      // Track successful status update
      telemetry.track('status_update_completed', {
        request_id: requestId,
        previous_status: previousStatus || 'unknown',
        new_status: newStatus,
        update_duration_ms: Date.now() - startTime,
      });
      
      toast({
        title: "Status updated",
        description: `Request status changed to ${newStatus === WarmIntroStatus.connected ? 'Approved' : newStatus}`,
      });
    } catch (err: unknown) {
      // Track failed status update
      telemetry.track('status_update_failed', {
        request_id: requestId,
        attempted_status: newStatus,
        error_type: typeof err === 'object' && err ? err.constructor.name : 'unknown',
      });
      
      toast({
        title: "Error",
        description: "Failed to update request status",
        variant: "destructive",
      });
    } finally {
      setUpdatingStatus(null);
    }
  };

  const handleOutcomeUpdate = async (requestId: string, outcome: string | null) => {
    if (!token) return;
    
    const request = requests.find(r => r.id === requestId);
    const startTime = Date.now();
    
    setUpdatingStatus(requestId);
    try {
      // Use the existing status update endpoint but only update the outcome
      const outcomeDate = outcome ? new Date().toISOString() : null;
      await updateWarmIntroRequestStatus(requestId, request!.status, token,
        request!.connected_date || undefined,
        request!.declined_date || undefined,
        outcome,
        outcomeDate
      );
      
      // Optimistically update the local state
      setRequests(prev => prev.map(req =>
        req.id === requestId
          ? {
              ...req,
              outcome: outcome,
              outcome_date: outcomeDate,
              updated_at: new Date().toISOString()
            }
          : req
      ));
      
      toast({
        title: "Outcome updated",
        description: `Connection outcome set to ${outcome || 'reset'}`,
      });
    } catch (err: unknown) {
      toast({
        title: "Error",
        description: "Failed to update outcome",
        variant: "destructive",
      });
    } finally {
      setUpdatingStatus(null);
    }
  };

  const handleStatusButtonClick = (requestId: string, newStatus: WarmIntroStatus) => {
    if (newStatus === WarmIntroStatus.connected || newStatus === WarmIntroStatus.declined) {
      // Show date picker modal
      setDatePickerModal({
        isOpen: true,
        requestId,
        status: newStatus,
        title: `Set ${newStatus === WarmIntroStatus.connected ? 'Approved' : 'Declined'} Date`,
        description: `Please select the date when this request was ${newStatus === WarmIntroStatus.connected ? 'approved' : 'declined'}.`
      });
    } else {
      // For pending status, update directly without date
      handleStatusUpdate(requestId, newStatus);
    }
  };

  const handleDateConfirm = (selectedDate: string) => {
    handleStatusUpdate(datePickerModal.requestId, datePickerModal.status, selectedDate);
    setDatePickerModal(prev => ({ ...prev, isOpen: false }));
  };

  const handleDateCancel = () => {
    setDatePickerModal(prev => ({ ...prev, isOpen: false }));
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      telemetry.track('requests_page_paginated', {
        previous_page: currentPage,
        new_page: newPage,
        total_pages: totalPages,
        status_filter: statusFilter,
      });
      updateURL(newPage, undefined);
    }
  };

  const handleStatusChange = (newStatus: string) => {
    telemetry.track('requests_page_filtered', {
      previous_filter: statusFilter,
      new_filter: newStatus,
      results_count: totalRequests,
    });
    updateURL(1, newStatus); // Reset to page 1 when changing status
  };

  const handleRefresh = () => {
    telemetry.track('requests_page_refreshed', {
      current_page: currentPage,
      status_filter: statusFilter,
      manual_refresh: true,
    });
    fetchRequests(currentPage, statusFilter);
  };

  const handleExportCSV = async () => {
    if (!token) return;
    
    setExportingCSV(true);
    try {
      const blob = await exportConnectedRequestsCSV(token);
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `connected_warm_intro_requests_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast({
        title: "Export successful",
        description: "Connected requests have been exported to CSV",
      });
    } catch {
      toast({
        title: "Export failed",
        description: "Failed to export connected requests",
        variant: "destructive",
      });
    } finally {
      setExportingCSV(false);
    }
  };

  const getStatusBadgeVariant = (status: WarmIntroStatus) => {
    switch (status) {
      case WarmIntroStatus.pending:
        return "secondary";
      case WarmIntroStatus.connected:
        return "default";
      case WarmIntroStatus.declined:
        return "destructive";
      default:
        return "secondary";
    }
  };

  const getStatusColor = (status: WarmIntroStatus) => {
    switch (status) {
      case WarmIntroStatus.pending:
        return "text-yellow-600 bg-yellow-50 border-yellow-200";
      case WarmIntroStatus.connected:
        return "text-green-600 bg-green-50 border-green-200";
      case WarmIntroStatus.declined:
        return "text-red-600 bg-red-50 border-red-200";
      default:
        return "text-gray-600 bg-gray-50 border-gray-200";
    }
  };

  const get14DayOutcome = (request: WarmIntroRequest) => {
    // If status is declined, return N/A regardless of other logic
    if (request.status === WarmIntroStatus.declined) {
      return "N/A";
    }
    
    // If outcome exists, display it
    if (request.outcome) {
      return request.outcome;
    }
    
    // If outcome is null, check if request is more than 14 days old
    const createdDate = new Date(request.created_at);
    const fourteenDaysAgo = new Date();
    fourteenDaysAgo.setDate(fourteenDaysAgo.getDate() - 14);
    
    if (createdDate < fourteenDaysAgo) {
      return "No response";
    } else {
      return "N/A";
    }
  };

  if (loading && requests.length === 0) {
    return (
      <div className="container mx-auto p-4">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-6 h-6 animate-spin mr-2" />
          <span>Loading warm intro requests...</span>
        </div>
      </div>
    );
  }

  if (error && requests.length === 0) {
    return (
      <div className="container mx-auto p-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-red-600">Error: {error}</p>
            <Button onClick={handleRefresh} className="mt-4">
              <RefreshCw className="w-4 h-4 mr-2" />
              Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Warm Intro Requests</h1>
          <p className="text-sm text-gray-600 mt-1">
            Manage and track your warm introduction requests
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCSV}
            disabled={exportingCSV}
          >
            <Download className={cn("w-4 h-4 mr-2", exportingCSV && "animate-spin")} />
            Export Connected
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={loading}
          >
            <RefreshCw className={cn("w-4 h-4 mr-2", loading && "animate-spin")} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="py-3">
          <CardHeader className="pb-1">
            <CardDescription>Total Requests</CardDescription>
            <CardTitle className="text-2xl">{totalRequests}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="py-3">
          <CardHeader className="pb-1">
            <CardDescription>Pending</CardDescription>
            <CardTitle className="text-2xl text-yellow-600">
              {statusCounts.pending}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card className="py-3">
          <CardHeader className="pb-1">
            <CardDescription>Approved</CardDescription>
            <CardTitle className="text-2xl text-green-600">
              {statusCounts.connected}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card className="py-3">
          <CardHeader className="pb-1">
            <CardDescription>Denied</CardDescription>
            <CardTitle className="text-2xl text-red-600">
              {statusCounts.declined}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Filters - Segmented Control */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">Status:</span>
            </div>
            <div className="flex flex-wrap gap-1 p-1 bg-gray-100 rounded-lg w-fit">
              <button
                onClick={() => handleStatusChange('all')}
                className={cn(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-200",
                  statusFilter === 'all'
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                )}
              >
                All
              </button>
              <button
                onClick={() => handleStatusChange(WarmIntroStatus.pending)}
                className={cn(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-200",
                  statusFilter === WarmIntroStatus.pending
                    ? "bg-white text-yellow-700 shadow-sm"
                    : "text-gray-600 hover:text-yellow-700 hover:bg-yellow-50"
                )}
              >
                Pending
              </button>
              <button
                onClick={() => handleStatusChange(WarmIntroStatus.connected)}
                className={cn(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-200",
                  statusFilter === WarmIntroStatus.connected
                    ? "bg-white text-green-700 shadow-sm"
                    : "text-gray-600 hover:text-green-700 hover:bg-green-50"
                )}
              >
                Approved
              </button>
              <button
                onClick={() => handleStatusChange(WarmIntroStatus.declined)}
                className={cn(
                  "px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-200",
                  statusFilter === WarmIntroStatus.declined
                    ? "bg-white text-red-700 shadow-sm"
                    : "text-gray-600 hover:text-red-700 hover:bg-red-50"
                )}
              >
                Denied
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Requester</TableHead>
                  <TableHead>Connection</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead>Request approved?</TableHead>
                  <TableHead>14 Day Outcome</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {requests.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                      No warm intro requests found
                    </TableCell>
                  </TableRow>
                ) : (
                  requests.map(request => (
                    <TableRow key={request.id}>
                      <TableCell className="font-medium">
                        {request.requester_name}
                      </TableCell>
                      <TableCell>{request.connection_name}</TableCell>
                      <TableCell>
                        <Badge
                          variant={getStatusBadgeVariant(request.status)}
                          className={cn("capitalize", getStatusColor(request.status))}
                        >
                          {request.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {new Date(request.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {new Date(request.updated_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {request.status === WarmIntroStatus.pending && (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleStatusButtonClick(request.id, WarmIntroStatus.connected)}
                                disabled={updatingStatus === request.id}
                                className="text-green-600 border-green-200 hover:bg-green-50"
                              >
                                Approved
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleStatusButtonClick(request.id, WarmIntroStatus.declined)}
                                disabled={updatingStatus === request.id}
                                className="text-red-600 border-red-200 hover:bg-red-50"
                              >
                                Declined
                              </Button>
                            </>
                          )}
                          {request.status !== WarmIntroStatus.pending && (
                            <div className="flex flex-col gap-2">
                              {/* Show date if available */}
                              {request.status === WarmIntroStatus.connected && request.connected_date && (
                                <div className="text-xs text-green-600 font-medium">
                                  Approved: {new Date(request.connected_date).toLocaleDateString()}
                                </div>
                              )}
                              {request.status === WarmIntroStatus.declined && request.declined_date && (
                                <div className="text-xs text-red-600 font-medium">
                                  Declined: {new Date(request.declined_date).toLocaleDateString()}
                                </div>
                              )}
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleStatusButtonClick(request.id, WarmIntroStatus.pending)}
                                disabled={updatingStatus === request.id}
                                className="text-yellow-600 border-yellow-200 hover:bg-yellow-50"
                              >
                                Reset
                              </Button>
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {request.outcome ? (
                            <div className="flex flex-col gap-2">
                              {request.outcome_date && (
                                <div className={cn(
                                  "text-xs font-medium",
                                  request.outcome === "Connected" ? "text-green-600" : "text-red-600"
                                )}>
                                  {request.outcome === "Connected" ? "Connected" : "Not Connected"}: {new Date(request.outcome_date).toLocaleDateString()}
                                </div>
                              )}
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleOutcomeUpdate(request.id, null)}
                                disabled={updatingStatus === request.id}
                                className="text-yellow-600 border-yellow-200 hover:bg-yellow-50"
                              >
                                Reset
                              </Button>
                            </div>
                          ) : (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleOutcomeUpdate(request.id, "Connected")}
                                disabled={updatingStatus === request.id}
                                className="text-green-600 border-green-200 hover:bg-green-50"
                              >
                                Connected
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleOutcomeUpdate(request.id, "Not Connected")}
                                disabled={updatingStatus === request.id}
                                className="text-red-600 border-red-200 hover:bg-red-50"
                              >
                                Not Connected
                              </Button>
                            </>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-600">
                Showing {((currentPage - 1) * limit) + 1} to {Math.min(currentPage * limit, totalRequests)} of {totalRequests} requests
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1 || loading}
                >
                  <ChevronLeft className="w-4 h-4" />
                  Previous
                </Button>
                <span className="text-sm text-gray-600">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages || loading}
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Date Picker Modal */}
      <DatePickerModal
        isOpen={datePickerModal.isOpen}
        onClose={handleDateCancel}
        onConfirm={handleDateConfirm}
        title={datePickerModal.title}
        description={datePickerModal.description}
        defaultDate={new Date().toISOString().split('T')[0]}
      />
    </div>
  );
}