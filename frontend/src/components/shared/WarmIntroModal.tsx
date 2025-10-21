"use client";

import React, { useState, useEffect, useCallback } from 'react';
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
import { WarmIntroStatus } from '@/lib/types';
import { useAuth } from '@/context/AuthContext';
import {
  X,
  Info,
  User,
  Linkedin,
  ChevronDown,
  ChevronUp,
  Check,
  Mail
} from 'lucide-react';

import { telemetry } from '@/lib/telemetry';

interface WarmIntroModalProps {
  isOpen: boolean;
  onClose: () => void;
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

const WarmIntroModal: React.FC<WarmIntroModalProps> = ({
  isOpen,
  onClose,
  targetFirstName,
  targetLastName,
  theirCompany,
  linkedinUrl,
  profilePicture,
}) => {
  const { toast } = useToast();
  const { token } = useAuth();
  const [showExample, setShowExample] = useState(false);
  const [requesterName, setRequesterName] = useState('');
  const [requesterLinkedIn, setRequesterLinkedIn] = useState('');
  const [reason, setReason] = useState('');
  const [about, setAbout] = useState('');
  const [includeEmail, setIncludeEmail] = useState(false);
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [errors, setErrors] = useState<{[key: string]: string}>({});
  const [touched, setTouched] = useState<{[key: string]: boolean}>({});
  const [modalOpenTime, setModalOpenTime] = useState<number>(0);

  // Validation
  const validateName = (name: string) => {
    if (name.length < 2) return "Please enter at least 2 characters.";
    if (name.length > 100) return "Name must be less than 100 characters.";
    if (!/^[a-zA-Z\s\-']+$/.test(name)) return "Name can only contain letters, spaces, hyphens, and apostrophes.";
    return "";
  };

  const validateLinkedIn = (url: string) => {
    const pattern = /^https?:\/\/(www\.)?linkedin\.com\/in\/[A-Za-z0-9\-_%]+\/?$/;
    if (!pattern.test(url)) return "Please enter a valid LinkedIn profile URL.";
    return "";
  };

  const validateTextarea = (text: string, fieldName: string) => {
    if (text.length < 20) return `Please add a bit more detail so this request is clear.`;
    if (text.length > 500) return `${fieldName} must be less than 500 characters.`;
    return "";
  };

  const validateEmail = useCallback((email: string) => {
    if (includeEmail && email.length === 0) return "Email is required when including email option is selected.";
    if (email.length > 0 && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return "Please enter a valid email address.";
    return "";
  }, [includeEmail]);

  // Real-time validation
  useEffect(() => {
    const newErrors: {[key: string]: string} = {};
    
    if (touched.requesterName) newErrors.requesterName = validateName(requesterName);
    if (touched.requesterLinkedIn) newErrors.requesterLinkedIn = validateLinkedIn(requesterLinkedIn);
    if (touched.reason) newErrors.reason = validateTextarea(reason, "Reason");
    if (touched.about) newErrors.about = validateTextarea(about, "About");
    if (touched.email) newErrors.email = validateEmail(email);

    setErrors(newErrors);
  }, [requesterName, requesterLinkedIn, reason, about, email, includeEmail, touched, validateEmail]);

  const isFormValid = 
    requesterName.length >= 2 && 
    validateLinkedIn(requesterLinkedIn) === "" &&
    reason.length >= 20 && 
    about.length >= 20 &&
    (!includeEmail || (email.length > 0 && validateEmail(email) === ""));

  // Autosave functionality
  const saveToLocalStorage = useCallback(() => {
    const draft = {
      requesterName,
      requesterLinkedIn,
      reason,
      about,
      includeEmail,
      email,
      targetName: `${targetFirstName} ${targetLastName}`,
      timestamp: Date.now()
    };
    localStorage.setItem('warmIntroModal_draft', JSON.stringify(draft));
  }, [requesterName, requesterLinkedIn, reason, about, includeEmail, email, targetFirstName, targetLastName]);

  // Debounced autosave
  useEffect(() => {
    const timer = setTimeout(() => {
      if (requesterName || requesterLinkedIn || reason || about || email) {
        saveToLocalStorage();
      }
    }, 2000);

    return () => clearTimeout(timer);
  }, [requesterName, requesterLinkedIn, reason, about, email, saveToLocalStorage]);

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
            setRequesterName(draft.requesterName || '');
            setRequesterLinkedIn(draft.requesterLinkedIn || '');
            setReason(draft.reason || '');
            setAbout(draft.about || '');
            setIncludeEmail(draft.includeEmail || false);
            setEmail(draft.email || '');
            
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
    const hasUnsavedChanges = requesterName || requesterLinkedIn || reason || about || email;
    
    if (hasUnsavedChanges) {
      if (confirm('You have unsaved changes. Are you sure you want to close?')) {
        telemetry.track('modal_closed', {
          target_name: `${targetFirstName} ${targetLastName}`,
          form_completion_percentage: telemetry.calculateFormCompletion({
            requesterName,
            requesterLinkedIn,
            reason,
            about,
            email: includeEmail ? email : 'not_required',
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
  }, [requesterName, requesterLinkedIn, reason, about, email, targetFirstName, targetLastName, modalOpenTime, onClose]);

  const resetForm = () => {
    setRequesterName('');
    setRequesterLinkedIn('');
    setReason('');
    setAbout('');
    setIncludeEmail(false);
    setEmail('');
    setShowSuccess(false);
    setErrors({});
    setTouched({});
    localStorage.removeItem('warmIntroModal_draft');
  };

  const handleBlur = (field: string) => {
    setTouched(prev => ({ ...prev, [field]: true }));
  };

  const handleChipClick = (chip: { label: string; text: string; }) => {
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
      const firstErrorKeys = Object.keys(errors);
      if (firstErrorKeys.length > 0) {
        const firstErrorId = firstErrorKeys[0];
        document.getElementById(firstErrorId)?.focus();
        document.getElementById(firstErrorId)?.scrollIntoView({ behavior: 'smooth' });
      }
      return;
    }

    setIsSubmitting(true);
    
    telemetry.track('email_generation_started', {
      requester_name_length: requesterName.length,
      reason_length: reason.length,
      about_length: about.length,
      include_email: includeEmail,
      target_name: `${targetFirstName} ${targetLastName}`,
    });

    try {
      // Step 1: Open the email client immediately to avoid popup blockers.
      const subject = encodeURIComponent(`Intro to ${targetFirstName} ${targetLastName}`);
      const targetInfo = `${targetFirstName} ${targetLastName}`;
      const targetLinkedInLine = linkedinUrl ? `LinkedIn: ${linkedinUrl}` : '';
      const requesterLinkedInLine = requesterLinkedIn ? `LinkedIn: ${requesterLinkedIn}` : '';
      const emailLine = includeEmail && email ? `Email: ${email}` : '';
      
      const emailBody = `Hi Ha,\n\nThank you for offering to make an introduction to ${targetInfo}.\n${targetLinkedInLine}\n\n${reason}\n\n${about}\n\nThanks again for helping connect us — I truly appreciate it.\n\nRegards,\n${requesterName}\n${requesterLinkedInLine}\n${emailLine}`;
      const encodedBody = encodeURIComponent(emailBody);
      const mailtoUrl = `mailto:ha@nextstepfwd.com?subject=${subject}&body=${encodedBody}`;
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Use the same simple approach as access requests - just use window.open
      let emailOpened = false;
      
      try {
        const emailWindow = window.open(mailtoUrl, '_blank');
        if (emailWindow) {
          emailOpened = true;
          telemetry.track('email_client_opened', {
            method: 'window_open',
            email_length: emailBody.length,
          });
        }
      } catch (e) {
        console.warn('Window open method failed:', e);
      }

      if (emailOpened) {
        // Create WarmIntroRequest record in database
        try {
          await createWarmIntroRequest(
            requesterName,
            `${targetFirstName} ${targetLastName}`,
            WarmIntroStatus.pending,
            token!
          );
          telemetry.track('warm_intro_request_created', {
            requester_name: requesterName,
            connection_name: `${targetFirstName} ${targetLastName}`,
            creation_method: 'success',
          });
        } catch (dbError) {
          // Log the error but don't fail the entire flow since email was sent successfully
          console.error('Failed to create WarmIntroRequest record:', dbError);
          telemetry.track('warm_intro_request_creation_failed', {
            error_type: typeof dbError === 'object' && dbError ? dbError.constructor.name : 'unknown',
            requester_name: requesterName,
            connection_name: `${targetFirstName} ${targetLastName}`,
          });
          
          // Show a non-blocking warning toast
          toast({
            title: "Request Submitted!",
            description: `Your email client should now be open. Please send the email to finalize the intro request for ${targetFirstName}.`,
            duration: 6000,
          });
        }
      } else {
        console.log('window.open was blocked or failed. Attempting fallback.');
        telemetry.track('email_fallback_used', {
          fallback_method: 'clipboard',
          email_length: emailBody.length,
        });
        // Fallback to clipboard if window.open is blocked
        try {
          const fullEmailContent = `To: ha@nextstepfwd.com\nSubject: ${decodeURIComponent(subject)}\n\n${emailBody}`;
          navigator.clipboard.writeText(fullEmailContent);
          toast({
            title: "Email content copied!",
            description: "We couldn't open your email client automatically, but we've copied the email content to your clipboard. Please paste it into your email client to continue.",
            duration: 8000,
          });
        } catch {
          const emailContent = `To: ha@nextstepfwd.com\nSubject: ${decodeURIComponent(subject)}\n\n${emailBody}`;
          alert(`Please copy this email content and send it manually:\n\n${emailContent}`);
        }
      }

      // Step 2: Create the WarmIntroRequest record in the database.
      // This now happens after attempting to open the email client.
      await createWarmIntroRequest(
        requesterName,
        `${targetFirstName} ${targetLastName}`,
        WarmIntroStatus.pending,
        token!
      );

      telemetry.track('warm_intro_request_created', {
        requester_name: requesterName,
        connection_name: `${targetFirstName} ${targetLastName}`,
        creation_method: 'success',
      });

      // Close modal and reset form after successful submission and email client attempt
      onClose();
      resetForm();

    } catch (error) {
      console.error('An error occurred during the warm intro request process:', error);
      telemetry.track('warm_intro_request_creation_failed', {
        error_type: typeof error === 'object' && error ? error.constructor.name : 'unknown',
        requester_name: requesterName,
        connection_name: `${targetFirstName} ${targetLastName}`,
      });
      toast({
        title: "Submission Error",
        description: "We couldn't save your request to our database. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [isFormValid, errors, requesterName, reason, about, includeEmail, email, targetFirstName, targetLastName, linkedinUrl, requesterLinkedIn, token, toast, onClose, resetForm]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        handleClose();
      }
      
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        if (isFormValid && document.activeElement?.tagName !== 'TEXTAREA') {
          handleSubmit();
        }
      }
    };

    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, isFormValid, handleClose, handleSubmit]);

  if (showSuccess) {
    return (
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="sm:max-w-[640px] p-8">
          <div className="text-center space-y-6">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
              <Check className="w-8 h-8 text-green-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Request sent</h2>
              <p className="text-gray-600">We will reach out to {targetFirstName} {targetLastName} and follow up with you.</p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button onClick={() => { onClose(); resetForm(); }} className="px-6 cursor-pointer">
                Close
              </Button>
              <Button
                variant="ghost"
                onClick={() => { setShowSuccess(false); resetForm(); }}
                className="text-sm cursor-pointer"
              >
                Make another intro request
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[640px] max-h-[90vh] overflow-y-auto p-6 sm:p-8">
        {/* Header */}
        <DialogHeader className="space-y-4 pb-6">
          <div className="flex items-center justify-between">
            <DialogTitle className="text-xl font-semibold text-gray-900">
              Request a Warm Intro
            </DialogTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClose}
              className="h-8 w-8 p-0"
              title="Cancel"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          
          {/* Byline */}
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center overflow-hidden">
              {profilePicture ? (
                <Image
                  src={profilePicture}
                  alt={targetFirstName}
                  className="w-full h-full object-cover"
                  width={32}
                  height={32}
                  onError={(e) => {
                    // Fallback to initials if image fails to load
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                    const parent = target.parentElement;
                    if (parent) {
                      parent.innerHTML = `<span class="text-white font-semibold text-xs">${targetFirstName?.[0] || ''}${targetLastName?.[0] || ''}</span>`;
                    }
                  }}
                />
              ) : (
                <span className="text-white font-semibold text-xs">
                  {targetFirstName || ''}{targetLastName || ''}
                </span>
              )}
            </div>
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

          {/* Your Information Section */}
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
                  onChange={(e) => setRequesterName(e.target.value)}
                  onBlur={() => handleBlur('requesterName')}
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
                    onChange={(e) => setRequesterLinkedIn(e.target.value)}
                    onBlur={() => handleBlur('requesterLinkedIn')}
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
          </div>

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
                  onChange={(e) => setReason(e.target.value)}
                  onBlur={() => handleBlur('reason')}
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
                  onChange={(e) => setAbout(e.target.value)}
                  onBlur={() => handleBlur('about')}
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
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="includeEmail"
                  checked={includeEmail}
                  onChange={(e) => setIncludeEmail(e.target.checked)}
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
                      onChange={(e) => setEmail(e.target.value)}
                      onBlur={() => handleBlur('email')}
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
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-6 border-t border-gray-200 space-y-4">
          <div className="flex flex-col sm:flex-row gap-3 justify-end">
            <Button variant="ghost" onClick={handleClose} className="sm:order-1 cursor-pointer">
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={!isFormValid || isSubmitting}
              className="sm:order-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Submitting...' : 'Submit for Review'}
            </Button>
          </div>
          <p className="text-xs text-gray-500 text-center">
            {/* We will not share your contact info without your consent. */}
  z          Your name, email, and LinkedIn profile will be shared with {targetFirstName} and Ha.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default WarmIntroModal;