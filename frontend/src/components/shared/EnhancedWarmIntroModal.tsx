
"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Image from 'next/image';
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
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { createWarmIntroRequest } from '@/lib/api';
import { WarmIntroStatus, User } from '@/lib/types';
import { useAuth } from '@/context/AuthContext';
import {
  X,
  Info,
  User as UserIcon,
  Linkedin,
  ChevronDown,
  ChevronUp,
  Check,
  Mail
} from 'lucide-react';

import { telemetry } from '@/lib/telemetry';

interface EnhancedWarmIntroModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void; // New callback for success handling
  targetFirstName: string;
  targetLastName: string;
  theirCompany: string;
  linkedinUrl?: string;
  profilePicture?: string;
}

const QUICK_CHIPS = [
  { label: "Career advice", text: "I'm exploring career opportunities in " },
  { label: "Role fit", text: "I'm interested in learning about roles at " },
  { label: "Partnership", text: "I'm exploring potential partnerships with " },
  { label: "Customer discovery", text: "I'm conducting customer discovery for " }
];

const EXAMPLE_TEMPLATE = {
  reason: "I am exploring pilots for an AI-powered customer support tool for retail. I would value your perspective on rollout pitfalls.",
  about: "I led CS Ops at Sam's Club and recently shipped a triage workflow with 18 percent faster resolution. If helpful, I can share a brief teardown of your public help center and offer to guest share our findings with your team."
};

const EnhancedWarmIntroModal: React.FC<EnhancedWarmIntroModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  targetFirstName,
  targetLastName,
  theirCompany,
  linkedinUrl,
  profilePicture,
}) => {
  const { toast } = useToast();
  const { token, user } = useAuth();
  const [showExample, setShowExample] = useState(false);
  const [reason, setReason] = useState('');
  const [about, setAbout] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<{[key: string]: string}>({});
  const [touched, setTouched] = useState<{[key: string]: boolean}>({});
  const [modalOpenTime, setModalOpenTime] = useState<number>(0);

  // Get user info from auth context
  const requesterName = user ? `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.email : '';
  const requesterLinkedIn = user?.linkedin_url || '';
  const email = user?.email || '';

  // Memoized validation functions
  const validateTextarea = useCallback((text: string, fieldName: string) => {
    if (text.length < 20) return `Please add a bit more detail so this request is clear.`;
    if (text.length > 500) return `${fieldName} must be less than 500 characters.`;
    return "";
  }, []);

  // Memoized event handlers to prevent re-renders
  const handleReasonChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setReason(e.target.value);
  }, []);

  const handleAboutChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setAbout(e.target.value);
  }, []);

  // Real-time validation - debounced to prevent focus loss
  useEffect(() => {
    const timer = setTimeout(() => {
      const newErrors: {[key: string]: string} = {};
      
      if (touched.reason) newErrors.reason = validateTextarea(reason, "Reason");
      if (touched.about) newErrors.about = validateTextarea(about, "About");

      setErrors(newErrors);
    }, 300); // Debounce validation to prevent focus loss

    return () => clearTimeout(timer);
  }, [reason, about, touched, validateTextarea]);

  // Memoize form validation to prevent unnecessary re-calculations
  const isFormValid = useMemo(() =>
    reason.length >= 20 &&
    about.length >= 20,
    [reason, about]
  );


  // Autosave functionality - memoized to prevent unnecessary re-creation
  const saveToLocalStorage = useCallback(() => {
    const draft = {
      reason,
      about,
      targetName: `${targetFirstName} ${targetLastName}`,
      timestamp: Date.now()
    };
    localStorage.setItem('warmIntroModal_draft', JSON.stringify(draft));
  }, [reason, about, targetFirstName, targetLastName]);

  // Debounced autosave - increased delay to prevent focus loss
  useEffect(() => {
    const timer = setTimeout(() => {
      if (reason || about) {
        saveToLocalStorage();
      }
    }, 5000); // Increased from 2000ms to 5000ms to reduce interference

    return () => clearTimeout(timer);
  }, [reason, about, saveToLocalStorage]);

  // Load draft on open
  useEffect(() => {
    if (isOpen) {
      const openTime = Date.now();
      setModalOpenTime(openTime);
      
      telemetry.track('modal_opened', {
        target_name: `${targetFirstName} ${targetLastName}`,
        target_company: theirCompany,
        has_linkedin_url: !!linkedinUrl,
        has_profile_picture: !!profilePicture,
      });
      
      const savedDraft = localStorage.getItem('warmIntroModal_draft');
      if (savedDraft) {
        try {
          const draft = JSON.parse(savedDraft);
          const isRecent = Date.now() - draft.timestamp < 24 * 60 * 60 * 1000; // 24 hours
          
          if (isRecent && draft.targetName === `${targetFirstName} ${targetLastName}`) {
            setReason(draft.reason || '');
            setAbout(draft.about || '');
            
            const ageHours = Math.round((Date.now() - draft.timestamp) / (1000 * 60 * 60));
            telemetry.track('autosave_restored', {
              fields_restored: Object.keys(draft).filter(key =>
                key !== 'timestamp' && key !== 'targetName' && draft[key]
              ),
              age_hours: ageHours,
            });
          }
        } catch (e) {
          console.error('Failed to restore draft:', e);
        }
      }
    }
  }, [isOpen, targetFirstName, targetLastName, theirCompany, linkedinUrl, profilePicture]);

  const handleClose = useCallback(() => {
    const hasUnsavedChanges = reason || about;
    
    if (hasUnsavedChanges) {
      if (confirm('You have unsaved changes. Are you sure you want to close?')) {
        telemetry.track('modal_closed', {
          target_name: `${targetFirstName} ${targetLastName}`,
          form_completion_percentage: telemetry.calculateFormCompletion({
            reason,
            about,
          }),
          time_spent_seconds: telemetry.calculateTimeSpent(modalOpenTime),
          close_method: 'unsaved_warning',
        });
        onClose();
        resetForm();
      }
    } else {
      telemetry.track('modal_closed', {
        target_name: `${targetFirstName} ${targetLastName}`,
        form_completion_percentage: 0,
        time_spent_seconds: telemetry.calculateTimeSpent(modalOpenTime),
        close_method: 'button',
      });
      onClose();
      resetForm();
    }
  }, [reason, about, targetFirstName, targetLastName, modalOpenTime, onClose]);

  const resetForm = () => {
    setReason('');
    setAbout('');
    setErrors({});
    setTouched({});
    localStorage.removeItem('warmIntroModal_draft');
  };

  // Memoized blur handlers for each field to prevent re-renders
  const handleReasonBlur = useCallback(() => {
    setTouched(prev => ({ ...prev, reason: true }));
  }, []);

  const handleAboutBlur = useCallback(() => {
    setTouched(prev => ({ ...prev, about: true }));
  }, []);

  const handleChipClick = (chip: typeof QUICK_CHIPS[0]) => {
    const existingLength = reason.length;
    setReason(prev => prev + chip.text);
    telemetry.track('quick_chip_used', {
      chip_label: chip.label,
      chip_text: chip.text,
      existing_text_length: existingLength,
    });
  };

  const handleUseTemplate = () => {
    const confirmOverwrite = reason || about ?
      confirm('This will replace your current text. Continue?') : true;
    
    if (confirmOverwrite) {
      telemetry.track('example_template_applied', {
        target_name: `${targetFirstName} ${targetLastName}`,
        overwrite_existing: !!(reason || about),
        existing_reason_length: reason.length,
        existing_about_length: about.length,
      });
      setReason(EXAMPLE_TEMPLATE.reason);
      setAbout(EXAMPLE_TEMPLATE.about);
    }
  };

  const toggleExample = () => {
    setShowExample(!showExample);
    if (!showExample) {
      telemetry.track('example_template_viewed', {
        target_name: `${targetFirstName} ${targetLastName}`,
      });
    }
  };


  const handleSubmit = useCallback(async () => {
    if (!isFormValid) {
      // Focus first invalid field
      const firstError = Object.keys(errors)[0];
      if (firstError) {
        document.getElementById(firstError)?.focus();
        document.getElementById(firstError)?.scrollIntoView({ behavior: 'smooth' });
      }
      return;
    }

    setIsSubmitting(true);
    
    telemetry.track('email_generation_started', {
      requester_name_length: requesterName.length,
      reason_length: reason.length,
      about_length: about.length,
      include_email: true,
      target_name: `${targetFirstName} ${targetLastName}`,
    });

    try {
      // Send request to backend which will handle email sending via Gmail API
      await createWarmIntroRequest(
        requesterName,
        `${targetFirstName} ${targetLastName}`,
        WarmIntroStatus.pending,
        token!,
        linkedinUrl,
        undefined // connection email not available in this context
      );
      
      telemetry.track('warm_intro_request_created', {
        requester_name: requesterName,
        connection_name: `${targetFirstName} ${targetLastName}`,
        creation_method: 'success',
      });

      // Show success message
      toast({
        title: "Request sent successfully!",
        description: `Your warm intro request for ${targetFirstName} ${targetLastName} has been sent to Ha. You'll be notified once there's an update.`,
        duration: 5000,
      });
      
      // Call success callback to handle return to search results
      onSuccess();
      
      // Close modal and reset form
      resetForm();
      onClose();
      
    } catch (error) {
      telemetry.trackCustom('submit_error', {
        error_code: 'api_failed',
        error_type: typeof error === 'object' && error ? error.constructor.name : 'unknown',
        target_name: `${targetFirstName} ${targetLastName}`,
      });
      
      toast({
        title: "Error",
        description: "We encountered an error processing your request. Please try again or contact support.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [requesterName, targetFirstName, targetLastName, reason, about, email, linkedinUrl, requesterLinkedIn, token, toast, onSuccess, onClose, isFormValid, errors]);


  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        handleClose();
      }
    };

    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, handleClose]);

  // Memoized Form Step Component to prevent re-creation on every render
  const FormStep = useMemo(() => (
    <>
      {/* Header */}
      <DialogHeader className="space-y-4 pb-6">
        <div className="flex items-center justify-between">
          <DialogTitle className="text-xl font-semibold text-gray-900">
            Request a Warm Intro
          </DialogTitle>
        </div>
        
        {/* Byline */}
        <div className="flex items-center space-x-3">
          {/* <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center overflow-hidden">
            {profilePicture ? (
              <Image
                src={profilePicture}
                alt={targetFirstName}
                className="w-full h-full object-cover"
                width={32}
                height={32}
              />
            ) : (
              <UserIcon className="w-4 h-4 text-gray-500" />
            )}
          </div> */}
          <p className="text-sm text-gray-600">
            Ha will reach out to <span className="font-medium text-gray-900">{targetFirstName} {targetLastName}</span> to see if they are open to connecting.
          </p>
        </div>
        
        <p className="text-sm text-gray-600">Clear reasons increase your chance of a Yes.</p>
      </DialogHeader>

      {/* Info Banner */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
        <div className="flex items-start space-x-3">
          <Info className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-gray-700">
            What you write here will be shared with {targetFirstName}.
          </p>
        </div>
      </div>

      <div className="space-y-8">
        {/* Example Section */}
        <div className="space-y-4">
          <Button
            variant="ghost"
            onClick={toggleExample}
            className="h-auto p-0 text-sm font-medium text-gray-700 hover:text-gray-900"
          >
            <span>See an example</span>
            {showExample ? (
              <ChevronUp className="w-4 h-4 ml-2" />
            ) : (
              <ChevronDown className="w-4 h-4 ml-2" />
            )}
          </Button>
          
          {showExample && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 space-y-4">
              <div className="space-y-3">
                <h4 className="font-medium text-gray-900">Example request:</h4>
                <div className="space-y-3 text-sm text-gray-700">
                  <p><strong>Why connect:</strong> {EXAMPLE_TEMPLATE.reason}</p>
                  <p><strong>About you:</strong> {EXAMPLE_TEMPLATE.about}</p>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleUseTemplate}
                className="text-xs"
              >
                Use this template
              </Button>
            </div>
          )}
        </div>

        {/* Your Information Section
        <div className="space-y-6">
          <div className="border-b border-gray-200 pb-2">
            <h3 className="text-base font-medium text-gray-900">Your Information</h3>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label htmlFor="requesterName" className="text-sm font-medium text-gray-900">
                Your Full Name <span className="text-red-500">*</span>
              </Label>
              <Input
                id="requesterName"
                placeholder="Enter your full name"
                value={requesterName}
                onChange={handleRequesterNameChange}
                onBlur={handleRequesterNameBlur}
                maxLength={100}
                className={cn(
                  "text-sm",
                  errors.requesterName && touched.requesterName && "border-red-500 focus:border-red-500"
                )}
                aria-describedby="requesterName-error requesterName-counter"
              />
              <div className="flex justify-between items-center min-h-[20px]">
                <p id="requesterName-error" className="text-xs text-red-600" aria-live="polite">
                  {errors.requesterName && touched.requesterName && errors.requesterName}
                </p>
                <p id="requesterName-counter" className={cn(
                  "text-xs",
                  requesterName.length > 90 ? "text-amber-600" : "text-gray-500"
                )}>
                  {requesterName.length}/100
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="requesterLinkedIn" className="text-sm font-medium text-gray-900">
                Your LinkedIn Profile URL <span className="text-red-500">*</span>
              </Label>
              <div className="relative">
                <Linkedin className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  id="requesterLinkedIn"
                  placeholder="https://linkedin.com/in/yourprofile"
                  value={requesterLinkedIn}
                  onChange={handleRequesterLinkedInChange}
                  onBlur={handleRequesterLinkedInBlur}
                  className={cn(
                    "text-sm pl-10",
                    errors.requesterLinkedIn && touched.requesterLinkedIn && "border-red-500 focus:border-red-500"
                  )}
                  aria-describedby="requesterLinkedIn-error"
                />
              </div>
              <p id="requesterLinkedIn-error" className="text-xs text-red-600 min-h-[16px]" aria-live="polite">
                {errors.requesterLinkedIn && touched.requesterLinkedIn && errors.requesterLinkedIn}
              </p>
            </div>
          </div>
        </div> */}

        {/* Your Request Section */}
        <div className="space-y-6">
          <div className="border-b border-gray-200 pb-2">
            <h3 className="text-base font-medium text-gray-900">Your Request</h3>
          </div>
          
          {/* Quick Chips */}
          <div className="space-y-3">
            <p className="text-sm text-gray-600">Quick starters:</p>
            <div className="flex flex-wrap gap-2">
              {QUICK_CHIPS.map((chip) => (
                <Button
                  key={chip.label}
                  variant="outline"
                  size="sm"
                  onClick={() => handleChipClick(chip)}
                  className="text-xs h-7 px-3"
                >
                  {chip.label}
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="reason" className="text-sm font-medium text-gray-900">
              Why do you want to connect with {targetFirstName}? <span className="text-red-500">*</span>
            </Label>
            <p className="text-xs text-gray-600">
              Specific beats generic. Mention a project, interest, or shared context.
            </p>
            <div className="relative">
              <Textarea
                id="reason"
                placeholder="Share the context, goal, or topic you'd like to discuss..."
                value={reason}
                onChange={handleReasonChange}
                onBlur={handleReasonBlur}
                maxLength={500}
                className={cn(
                  "min-h-[120px] text-sm resize-none",
                  errors.reason && touched.reason && "border-red-500 focus:border-red-500"
                )}
                aria-describedby="reason-error reason-counter"
              />
            </div>
            <div className="flex justify-between items-center min-h-[20px]">
              <p id="reason-error" className="text-xs text-red-600" aria-live="polite">
                {errors.reason && touched.reason && errors.reason}
              </p>
              <p id="reason-counter" className={cn(
                "text-xs",
                reason.length > 480 ? "text-red-600" : reason.length > 450 ? "text-amber-600" : "text-gray-500"
              )}>
                {reason.length}/500
              </p>
            </div>
          </div>
        </div>

        {/* About You Section */}
        <div className="space-y-6">
          <div className="border-b border-gray-200 pb-2">
            <h3 className="text-base font-medium text-gray-900">About You</h3>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="about" className="text-sm font-medium text-gray-900">
              Tell {targetFirstName} a bit about yourself and why a connection could be valuable. <span className="text-red-500">*</span>
            </Label>
            <p className="text-xs text-gray-600">
              Your role, relevant work, and how this connection could help both of you.
            </p>
            <div className="relative">
              <Textarea
                id="about"
                placeholder="Your role, relevant work, and how a connection could be valuable for them..."
                value={about}
                onChange={handleAboutChange}
                onBlur={handleAboutBlur}
                maxLength={500}
                className={cn(
                  "min-h-[120px] text-sm resize-none",
                  errors.about && touched.about && "border-red-500 focus:border-red-500"
                )}
                aria-describedby="about-error about-counter"
              />
            </div>
            <div className="flex justify-between items-center min-h-[20px]">
              <p id="about-error" className="text-xs text-red-600" aria-live="polite">
                {errors.about && touched.about && errors.about}
              </p>
              <p id="about-counter" className={cn(
                "text-xs",
                about.length > 480 ? "text-red-600" : about.length > 450 ? "text-amber-600" : "text-gray-500"
              )}>
                {about.length}/500
              </p>
            </div>
          </div>

          {/* Email Toggle */}
          {/* <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="includeEmail"
                checked={includeEmail}
                onChange={handleIncludeEmailChange}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <Label htmlFor="includeEmail" className="text-sm text-gray-700">
                Include my email with the intro
              </Label>
            </div>
            
            {includeEmail && (
              <div className="space-y-2">
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="your.email@example.com"
                    value={email}
                    onChange={handleEmailChange}
                    onBlur={handleEmailBlur}
                    className={cn(
                      "text-sm pl-10",
                      errors.email && touched.email && "border-red-500 focus:border-red-500"
                    )}
                    aria-describedby="email-error"
                  />
                </div>
                <p id="email-error" className="text-xs text-red-600 min-h-[16px]" aria-live="polite">
                  {errors.email && touched.email && errors.email}
                </p>
              </div>
            )}
          </div> */}
        </div>
      </div>

      {/* Footer */}
      <div className="pt-6 border-t border-gray-200 space-y-4">
        <div className="flex flex-col sm:flex-row gap-3 justify-end">
          <Button variant="ghost" onClick={handleClose} className="sm:order-1">
            Cancel
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={!isFormValid || isSubmitting}
            className="sm:order-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-30"
          >
            {isSubmitting ? 'Sending...' : 'Send Request'}
          </Button>
        </div>
        <p className="text-xs text-gray-500 text-center">
          {/* We will not share your contact info without your consent. */}
          Your name, email, and LinkedIn profile will be shared with {targetFirstName} and Ha.
        </p>
      </div>
    </>
  ), [
    targetFirstName,
    targetLastName,
    profilePicture,
    showExample,
    reason,
    about,
    errors,
    touched,
    isFormValid,
    isSubmitting,
    handleClose,
    toggleExample,
    handleUseTemplate,
    handleReasonChange,
    handleAboutChange,
    handleReasonBlur,
    handleAboutBlur,
    handleChipClick,
    handleSubmit
  ]);

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[640px] max-h-[90vh] overflow-y-auto p-4 sm:p-6 lg:p-8 w-[95vw] sm:w-full">
        {FormStep}
      </DialogContent>
    </Dialog>
  );
};

export default EnhancedWarmIntroModal;
