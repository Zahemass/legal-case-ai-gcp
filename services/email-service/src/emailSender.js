const nodemailer = require('nodemailer');
const sgMail = require('@sendgrid/mail');
const fs = require('fs').promises;
const path = require('path');
const Handlebars = require('handlebars');
const juice = require('juice');

class EmailSender {
  constructor() {
    this.provider = process.env.EMAIL_PROVIDER || 'sendgrid'; // 'sendgrid' or 'smtp'
    this.transporter = null;
    this.templates = new Map();
    
    this.init();
  }

  async init() {
    try {
      if (this.provider === 'sendgrid') {
        await this.initSendGrid();
      } else if (this.provider === 'smtp') {
        await this.initSMTP();
      } else {
        throw new Error(`Unsupported email provider: ${this.provider}`);
      }
      
      await this.loadTemplates();
      console.log(`✅ Email service initialized with provider: ${this.provider}`);
      
    } catch (error) {
      console.error('❌ Email service initialization failed:', error);
      throw error;
    }
  }

  async initSendGrid() {
    const apiKey = process.env.SENDGRID_API_KEY;
    if (!apiKey) {
      throw new Error('SENDGRID_API_KEY environment variable is required');
    }
    
    sgMail.setApiKey(apiKey);
    
    // Test configuration
    try {
      // SendGrid doesn't have a direct test method, so we'll just verify the API key format
      if (!apiKey.startsWith('SG.')) {
        throw new Error('Invalid SendGrid API key format');
      }
      console.log('✅ SendGrid configured successfully');
    } catch (error) {
      throw new Error(`SendGrid configuration failed: ${error.message}`);
    }
  }

  async initSMTP() {
    const config = {
      host: process.env.SMTP_HOST,
      port: parseInt(process.env.SMTP_PORT) || 587,
      secure: process.env.SMTP_SECURE === 'true',
      auth: {
        user: process.env.SMTP_USER,
        pass: process.env.SMTP_PASS
      }
    };

    if (!config.host || !config.auth.user || !config.auth.pass) {
      throw new Error('SMTP configuration incomplete. Required: SMTP_HOST, SMTP_USER, SMTP_PASS');
    }

    this.transporter = nodemailer.createTransporter(config);
    
    // Test connection
    try {
      await this.transporter.verify();
      console.log('✅ SMTP configured successfully');
    } catch (error) {
      throw new Error(`SMTP configuration failed: ${error.message}`);
    }
  }

  async loadTemplates() {
    try {
      const templatesDir = path.join(__dirname, 'templates');
      const files = await fs.readdir(templatesDir);
      
      for (const file of files) {
        if (path.extname(file) === '.html') {
          const templateName = path.basename(file, '.html');
          const templatePath = path.join(templatesDir, file);
          const templateContent = await fs.readFile(templatePath, 'utf-8');
          
          // Compile Handlebars template
          const compiledTemplate = Handlebars.compile(templateContent);
          this.templates.set(templateName, compiledTemplate);
          
          console.log(`📧 Loaded email template: ${templateName}`);
        }
      }
      
      // Load default test template if no templates found
      if (this.templates.size === 0) {
        this.loadDefaultTemplates();
      }
      
      console.log(`✅ Loaded ${this.templates.size} email templates`);
      
    } catch (error) {
      console.error('❌ Failed to load email templates:', error);
      this.loadDefaultTemplates();
    }
  }

  loadDefaultTemplates() {
    // Default test template
    const testTemplate = Handlebars.compile(`
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>{{subject}}</title>
        <style>
          body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background-color: #2c5282; color: white; padding: 20px; text-align: center; }
          .content { padding: 20px; background-color: #f8f9fa; }
          .footer { padding: 10px; text-align: center; font-size: 12px; color: #666; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>{{serviceName}}</h1>
          </div>
          <div class="content">
            <h2>Test Email</h2>
            <p>This is a test email sent at {{testTime}}.</p>
            <p>If you received this email, the email service is working correctly.</p>
          </div>
          <div class="footer">
            <p>Legal Case AI Email Service</p>
          </div>
        </div>
      </body>
      </html>
    `);
    
    this.templates.set('test', testTemplate);
    console.log('✅ Loaded default templates');
  }

  async sendEmail({ to, subject, template, data = {}, priority = 'normal' }) {
    try {
      console.log(`📧 Sending email: ${template} to ${to}`);
      
      if (!this.templates.has(template)) {
        throw new Error(`Template '${template}' not found`);
      }

      // Prepare template data with defaults
      const templateData = {
        ...data,
        subject,
        currentYear: new Date().getFullYear(),
        timestamp: new Date().toISOString()
      };

      // Render template
      const compiledTemplate = this.templates.get(template);
      let htmlContent = compiledTemplate(templateData);
      
      // Inline CSS for better email client compatibility
      htmlContent = juice(htmlContent);

      // Generate plain text version
      const textContent = this.htmlToText(htmlContent);

      // Send email based on provider
      let result;
      if (this.provider === 'sendgrid') {
        result = await this.sendWithSendGrid(to, subject, htmlContent, textContent, priority);
      } else if (this.provider === 'smtp') {
        result = await this.sendWithSMTP(to, subject, htmlContent, textContent, priority);
      }

      console.log(`✅ Email sent successfully: ${template} to ${to}`);
      return { success: true, messageId: result.messageId };

    } catch (error) {
      console.error('❌ Email sending failed:', error);
      return { success: false, error: error.message };
    }
  }

  async sendWithSendGrid(to, subject, html, text, priority) {
    const msg = {
      to,
      from: {
        email: process.env.FROM_EMAIL || 'noreply@legalcaseai.com',
        name: process.env.FROM_NAME || 'Legal Case AI'
      },
      subject,
      text,
      html,
      trackingSettings: {
        clickTracking: { enable: true },
        openTracking: { enable: true }
      }
    };

    // Add priority header if specified
    if (priority === 'high') {
      msg.headers = { 'X-Priority': '1' };
    }

    const response = await sgMail.send(msg);
    return { messageId: response[0].headers['x-message-id'] };
  }

  async sendWithSMTP(to, subject, html, text, priority) {
    const mailOptions = {
      from: {
        name: process.env.FROM_NAME || 'Legal Case AI',
        address: process.env.FROM_EMAIL || 'noreply@legalcaseai.com'
      },
      to,
      subject,
      text,
      html
    };

    // Add priority header if specified
    if (priority === 'high') {
      mailOptions.headers = { 'X-Priority': '1' };
    }

    const info = await this.transporter.sendMail(mailOptions);
    return { messageId: info.messageId };
  }

  async sendBulkEmail(emails) {
    const results = [];
    const batchSize = 10; // Process in batches to avoid overwhelming the service
    
    for (let i = 0; i < emails.length; i += batchSize) {
      const batch = emails.slice(i, i + batchSize);
      const batchPromises = batch.map(email => this.sendEmail(email));
      
      try {
        const batchResults = await Promise.allSettled(batchPromises);
        
        batchResults.forEach((result, index) => {
          const email = batch[index];
          if (result.status === 'fulfilled') {
            results.push({
              to: email.to,
              success: result.value.success,
              messageId: result.value.messageId,
              error: result.value.error
            });
          } else {
            results.push({
              to: email.to,
              success: false,
              error: result.reason.message
            });
          }
        });
        
        // Small delay between batches
        if (i + batchSize < emails.length) {
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
        
      } catch (error) {
        // Handle batch errors
        batch.forEach(email => {
          results.push({
            to: email.to,
            success: false,
            error: error.message
          });
        });
      }
    }
    
    return results;
  }

  htmlToText(html) {
    // Simple HTML to text conversion
    return html
      .replace(/<style[^>]*>.*?<\/style>/gi, '')
      .replace(/<script[^>]*>.*?<\/script>/gi, '')
      .replace(/<[^>]+>/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  isConfigured() {
    if (this.provider === 'sendgrid') {
      return !!process.env.SENDGRID_API_KEY;
    } else if (this.provider === 'smtp') {
      return !!(process.env.SMTP_HOST && process.env.SMTP_USER && process.env.SMTP_PASS);
    }
    return false;
  }

  getProviderName() {
    return this.provider;
  }

  getTemplateNames() {
    return Array.from(this.templates.keys());
  }

  async testConnection() {
    try {
      if (this.provider === 'sendgrid') {
        // SendGrid doesn't have a direct test method
        return { success: true, provider: 'sendgrid' };
      } else if (this.provider === 'smtp') {
        await this.transporter.verify();
        return { success: true, provider: 'smtp' };
      }
    } catch (error) {
      return { success: false, error: error.message, provider: this.provider };
    }
  }
}

// Create singleton instance
const emailSender = new EmailSender();

module.exports = emailSender;