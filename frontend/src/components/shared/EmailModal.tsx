"use client";

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { Mail, Send, X } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

// Get API base URL
const getApiBaseUrl = () => {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    // Remove /api/v1 suffix if it exists to avoid duplication
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
    return baseUrl.replace(/\/api\/v1$/, '');
  }
  if (typeof window !== 'undefined') {
    return window.location.origin.replace(':3000', ':8000');
  }
  return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

interface EmailModalProps {
  isOpen: boolean;
  onClose: () => void;
  connectionName: string;
  connectionLinkedinUrl?: string;
  connectionEmail?: string;
}

const EMAIL_TEMPLATE = `Hi {connectionName},

I hope this email finds you well. I wanted to reach out regarding a warm introduction request that was made through SuperConnect AI.

{requesterName} has requested an introduction to you, and I wanted to facilitate this connection. They mentioned they're interested in connecting because:

{reason}

Here's a bit about {requesterName}:
{about}

Would you be open to a brief conversation or connection? I'd be happy to facilitate an introduction if you're interested.

Best regards,
Ha
SuperConnect AI`;

const EmailModal: React.FC<EmailModalProps> = ({
  isOpen,
  onClose,
  connectionName,
  connectionLinkedinUrl,
  connectionEmail,
}) => {
  const { toast } = useToast();
  const { token } = useAuth();
  const [recipientEmail, setRecipientEmail] = useState(connectionEmail || '');
  const [subject, setSubject] = useState(`Warm Introduction Request - ${connectionName}`);
  const [emailBody, setEmailBody] = useState(EMAIL_TEMPLATE.replace('{connectionName}', connectionName));
  const [isSending, setIsSending] = useState(false);

  const handleSendEmail = async () => {
    if (!recipientEmail.trim()) {
      toast({
        title: "Error",
        description: "Please enter a recipient email address",
        variant: "destructive",
      });
      return;
    }

    if (!emailBody.trim()) {
      toast({
        title: "Error",
        description: "Please enter email content",
        variant: "destructive",
      });
      return;
    }

    if (!token) {
      toast({
        title: "Error",
        description: "Authentication required",
        variant: "destructive",
      });
      return;
    }

    setIsSending(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/send-email`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          to_email: recipientEmail,
          subject: subject,
          body: emailBody,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      
      if (result.success) {
        toast({
          title: "Email sent successfully",
          description: result.message,
        });
        onClose();
      } else {
        throw new Error(result.message || 'Failed to send email');
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to send email. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSending(false);
    }
  };

  const handleUseTemplate = () => {
    setEmailBody(EMAIL_TEMPLATE.replace('{connectionName}', connectionName));
  };

  const handleClose = () => {
    setRecipientEmail(connectionEmail || '');
    setSubject(`Warm Introduction Request - ${connectionName}`);
    setEmailBody(EMAIL_TEMPLATE.replace('{connectionName}', connectionName));
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Mail className="w-5 h-5" />
            Send Email to {connectionName}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Connection Info */}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h3 className="font-medium text-gray-900 mb-2">Connection Details</h3>
            <div className="space-y-2 text-sm">
              <p><strong>Name:</strong> {connectionName}</p>
              {connectionLinkedinUrl && (
                <p>
                  <strong>LinkedIn:</strong>{' '}
                  <a
                    href={connectionLinkedinUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800"
                  >
                    View Profile
                  </a>
                </p>
              )}
              {connectionEmail && (
                <p><strong>Email:</strong> {connectionEmail}</p>
              )}
            </div>
          </div>

          {/* Email Form */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="recipientEmail">Recipient Email *</Label>
              <Input
                id="recipientEmail"
                type="email"
                placeholder="Enter recipient email address"
                value={recipientEmail}
                onChange={(e) => setRecipientEmail(e.target.value)}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="subject">Subject *</Label>
              <Input
                id="subject"
                placeholder="Enter email subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="emailBody">Email Content *</Label>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleUseTemplate}
                  className="text-xs"
                >
                  Use Template
                </Button>
              </div>
              <Textarea
                id="emailBody"
                placeholder="Enter email content"
                value={emailBody}
                onChange={(e) => setEmailBody(e.target.value)}
                className="min-h-[200px] resize-none"
              />
            </div>
          </div>

          {/* Template Info */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 mb-2">Template Variables</h4>
            <p className="text-sm text-blue-800">
              You can use these variables in your email: <code>{'{connectionName}'}</code>, <code>{'{requesterName}'}</code>, <code>{'{reason}'}</code>, <code>{'{about}'}</code>
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
          <Button variant="ghost" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSendEmail}
            disabled={isSending || !recipientEmail.trim() || !emailBody.trim()}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {isSending ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                Sending...
              </>
            ) : (
              <>
                <Send className="w-4 h-4 mr-2" />
                Send Email
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default EmailModal;
