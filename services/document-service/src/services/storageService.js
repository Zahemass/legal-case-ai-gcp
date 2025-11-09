// services/document-service/src/services/storageService.js
const { Storage } = require('@google-cloud/storage');
const crypto = require('crypto');

// Initialize Google Cloud Storage
const storage = new Storage();
const BUCKET_NAME = process.env.STORAGE_BUCKET || 'legal-case-documents';

class StorageService {
  constructor() {
    this.bucket = storage.bucket(BUCKET_NAME);
  }

  /**
   * Upload a file to Google Cloud Storage
   * @param {Buffer} fileBuffer - File buffer
   * @param {string} fileName - Destination file name
   * @param {Object} options - Upload options
   * @returns {Promise<Object>} Upload result
   */
  /**
 * Upload a file to Google Cloud Storage (UBLA-compatible)
 * @param {Buffer} fileBuffer - File buffer
 * @param {string} fileName - Destination file name
 * @param {Object} options - Upload options
 * @returns {Promise<Object>} Upload result
 */
async uploadFile(fileBuffer, fileName, options = {}) {
  try {
    const file = this.bucket.file(fileName);

    // ✅ Calculate checksum for file integrity
    const checksum = crypto.createHash('md5').update(fileBuffer).digest('hex');

    const uploadOptions = {
      metadata: {
        contentType: options.contentType || 'application/octet-stream',
        metadata: {
          uploadedAt: new Date().toISOString(),
          checksum,
          ...options.metadata
        }
      },
      resumable: fileBuffer.length > 10 * 1024 * 1024, // >10MB = resumable
      validation: 'md5'
    };

    // ✅ Upload file to GCS (no ACL changes)
    await file.save(fileBuffer, uploadOptions);

    // ❌ DO NOT call makePublic() — UBLA forbids per-object ACLs
    // if (options.makePublic) await file.makePublic();

    // ✅ Construct a stable reference URL (not actually public)
    const storageUrl = `https://storage.googleapis.com/${BUCKET_NAME}/${fileName}`;
    const gsUri = `gs://${BUCKET_NAME}/${fileName}`;

    // ✅ Fetch metadata
    const [metadata] = await file.getMetadata();

    console.log(`✅ File uploaded successfully: ${fileName} (${fileBuffer.length} bytes)`);

    return {
      fileName,
      size: fileBuffer.length,
      contentType: options.contentType,
      checksum,
      gsUri,
      storageUrl, // <-- use this instead of publicUrl
      metadata
    };

  } catch (error) {
    console.error(`❌ Error uploading file ${fileName}:`, error);
    throw new Error(`Failed to upload file: ${error.message}`);
  }
}


  /**
   * Generate a signed URL for file access
   * @param {string} fileName - File name
   * @param {string} action - Action type ('read', 'write', 'delete')
   * @param {number} expires - Expiration time in seconds
   * @returns {Promise<string>} Signed URL
   */
  async getSignedUrl(fileName, action = 'read', expires = 3600) {
    try {
      const file = this.bucket.file(fileName);
      
      const options = {
        version: 'v4',
        action: action,
        expires: Date.now() + expires * 1000
      };

      if (action === 'read') {
        options.responseDisposition = 'inline';
      }

      const [signedUrl] = await file.getSignedUrl(options);
      
      console.log(`✅ Generated signed URL for ${fileName} (${action}, expires in ${expires}s)`);
      return signedUrl;

    } catch (error) {
      console.error(`❌ Error generating signed URL for ${fileName}:`, error);
      throw new Error(`Failed to generate signed URL: ${error.message}`);
    }
  }

  /**
   * Check if a file exists
   * @param {string} fileName - File name
   * @returns {Promise<boolean>} File exists
   */
  async fileExists(fileName) {
    try {
      const file = this.bucket.file(fileName);
      const [exists] = await file.exists();
      return exists;
    } catch (error) {
      console.error(`❌ Error checking file existence ${fileName}:`, error);
      return false;
    }
  }

  /**
   * Delete a file from storage
   * @param {string} fileName - File name
   * @returns {Promise<boolean>} Deletion success
   */
  async deleteFile(fileName) {
    try {
      const file = this.bucket.file(fileName);
      await file.delete();
      
      console.log(`✅ File deleted successfully: ${fileName}`);
      return true;

    } catch (error) {
      if (error.code === 404) {
        console.log(`⚠️ File not found for deletion: ${fileName}`);
        return true; // Consider it successful if file doesn't exist
      }
      
      console.error(`❌ Error deleting file ${fileName}:`, error);
      throw new Error(`Failed to delete file: ${error.message}`);
    }
  }

  /**
   * Get file metadata
   * @param {string} fileName - File name
   * @returns {Promise<Object>} File metadata
   */
  async getFileMetadata(fileName) {
    try {
      const file = this.bucket.file(fileName);
      const [metadata] = await file.getMetadata();
      
      return {
        name: metadata.name,
        size: parseInt(metadata.size),
        contentType: metadata.contentType,
        created: metadata.timeCreated,
        updated: metadata.updated,
        md5Hash: metadata.md5Hash,
        crc32c: metadata.crc32c,
        generation: metadata.generation,
        customMetadata: metadata.metadata || {}
      };

    } catch (error) {
      console.error(`❌ Error getting file metadata ${fileName}:`, error);
      throw new Error(`Failed to get file metadata: ${error.message}`);
    }
  }

  /**
   * Copy a file within the bucket
   * @param {string} sourceFileName - Source file name
   * @param {string} destFileName - Destination file name
   * @returns {Promise<Object>} Copy result
   */
  async copyFile(sourceFileName, destFileName) {
    try {
      const sourceFile = this.bucket.file(sourceFileName);
      const destFile = this.bucket.file(destFileName);
      
      await sourceFile.copy(destFile);
      
      console.log(`✅ File copied successfully: ${sourceFileName} -> ${destFileName}`);
      
      return {
        sourceFileName,
        destFileName,
        success: true
      };

    } catch (error) {
      console.error(`❌ Error copying file ${sourceFileName} to ${destFileName}:`, error);
      throw new Error(`Failed to copy file: ${error.message}`);
    }
  }

  /**
   * Move a file within the bucket
   * @param {string} sourceFileName - Source file name
   * @param {string} destFileName - Destination file name
   * @returns {Promise<Object>} Move result
   */
  async moveFile(sourceFileName, destFileName) {
    try {
      const sourceFile = this.bucket.file(sourceFileName);
      const destFile = this.bucket.file(destFileName);
      
      await sourceFile.move(destFile);
      
      console.log(`✅ File moved successfully: ${sourceFileName} -> ${destFileName}`);
      
      return {
        sourceFileName,
        destFileName,
        success: true
      };

    } catch (error) {
      console.error(`❌ Error moving file ${sourceFileName} to ${destFileName}:`, error);
      throw new Error(`Failed to move file: ${error.message}`);
    }
  }

  /**
   * List files in the bucket with optional prefix
   * @param {string} prefix - File prefix filter
   * @param {Object} options - List options
   * @returns {Promise<Array>} List of files
   */
  async listFiles(prefix = '', options = {}) {
    try {
      const listOptions = {
        prefix,
        maxResults: options.maxResults || 1000,
        delimiter: options.delimiter
      };

      if (options.pageToken) {
        listOptions.pageToken = options.pageToken;
      }

      const [files, , apiResponse] = await this.bucket.getFiles(listOptions);
      
      const fileList = files.map(file => ({
        name: file.name,
        size: parseInt(file.metadata.size),
        contentType: file.metadata.contentType,
        created: file.metadata.timeCreated,
        updated: file.metadata.updated
      }));

      return {
        files: fileList,
        nextPageToken: apiResponse.nextPageToken,
        prefixes: apiResponse.prefixes || []
      };

    } catch (error) {
      console.error(`❌ Error listing files with prefix ${prefix}:`, error);
      throw new Error(`Failed to list files: ${error.message}`);
    }
  }

  /**
   * Get download stream for a file
   * @param {string} fileName - File name
   * @returns {Promise<Stream>} Download stream
   */
  async getDownloadStream(fileName) {
    try {
      const file = this.bucket.file(fileName);
      return file.createReadStream();
    } catch (error) {
      console.error(`❌ Error creating download stream for ${fileName}:`, error);
      throw new Error(`Failed to create download stream: ${error.message}`);
    }
  }

  /**
   * Upload from stream
   * @param {Stream} stream - Upload stream
   * @param {string} fileName - Destination file name
   * @param {Object} options - Upload options
   * @returns {Promise<Object>} Upload result
   */
  async uploadFromStream(stream, fileName, options = {}) {
    try {
      const file = this.bucket.file(fileName);
      
      const uploadStream = file.createWriteStream({
        metadata: {
          contentType: options.contentType || 'application/octet-stream',
          metadata: options.metadata || {}
        },
        resumable: options.resumable !== false
      });

      return new Promise((resolve, reject) => {
        stream.pipe(uploadStream)
          .on('error', reject)
          .on('finish', async () => {
            try {
              const [metadata] = await file.getMetadata();
              console.log(`✅ Stream upload completed: ${fileName}`);
              resolve({
                fileName,
                size: parseInt(metadata.size),
                contentType: metadata.contentType,
                gsUri: `gs://${BUCKET_NAME}/${fileName}`
              });
            } catch (error) {
              reject(error);
            }
          });
      });

    } catch (error) {
      console.error(`❌ Error uploading from stream to ${fileName}:`, error);
      throw new Error(`Failed to upload from stream: ${error.message}`);
    }
  }

  /**
   * Generate resumable upload URL
   * @param {string} fileName - File name
   * @param {Object} options - Upload options
   * @returns {Promise<string>} Resumable upload URL
   */
  async generateResumableUploadUrl(fileName, options = {}) {
    try {
      const file = this.bucket.file(fileName);
      
      const [url] = await file.generateResumableUploadSignedUrl({
        version: 'v4',
        action: 'write',
        expires: Date.now() + (options.expires || 3600) * 1000,
        contentType: options.contentType,
        extensionHeaders: options.headers || {}
      });

      console.log(`✅ Generated resumable upload URL for ${fileName}`);
      return url;

    } catch (error) {
      console.error(`❌ Error generating resumable upload URL for ${fileName}:`, error);
      throw new Error(`Failed to generate resumable upload URL: ${error.message}`);
    }
  }
}

module.exports = new StorageService();