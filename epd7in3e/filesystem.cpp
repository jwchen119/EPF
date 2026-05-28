#include <filesystem.h>
#include <Arduino.h>
#include <SPIFFS.h>

bool fs_init(void)
{
    if (!SPIFFS.begin(true))
    {
        Serial.println(F("SPIFFS mount failed — check partition scheme (needs SPIFFS partition)"));
        return false;  // non-fatal: WiFi credentials stored in NVS/Preferences, not SPIFFS
    }
    else
    {
        Serial.println(F("Filesystem initialized"));
        return true;
    }
}

/**
 * @brief Function to de-init the filesystem
 * @param none
 * @return none
 */
void fs_deinit(void)
{
    SPIFFS.end();
}

// /**
//  * @brief Function to read data from file
//  * @param name filename
//  * @param out_buffer pointer to output buffer
//  * @return result - true if success; false - if failed
//  */
// bool fs_read_from_file(const char *name, uint8_t *out_buffer, size_t size)
// {
//     if (SPIFFS.exists(name))
//     {
//         File file = SPIFFS.open(name, FILE_READ);
//         if (file)
//         {
//             file.readBytes((char *)out_buffer, size);
//             return true;
//         }
//         else
//         {
//             return false;
//         }
//     }
//     else
//     {
//         return false;
//     }
// }

// /**
//  * @brief Function to write data to file
//  * @param name filename
//  * @param in_buffer pointer to input buffer
//  * @param size size of the input buffer
//  * @return size of written bytes
//  */
// size_t fs_write_to_file(const char *name, uint8_t *in_buffer, size_t size)
// {
//     uint32_t SPIFFS_freeBytes = (SPIFFS.totalBytes() - SPIFFS.usedBytes());
//     if (SPIFFS.exists(name))
//     {
//       SPIFFS.remove(name);
//     }
//     else
//     {
//       Serial.println("file not exsist.");
//     }
//     delay(100);
//     File file = SPIFFS.open(name, FILE_WRITE);
//     if (file)
//     {
//         // Write the buffer in chunks
//         size_t bytesWritten = 0;
//         while (bytesWritten < size)
//         {

//             size_t diff = size - bytesWritten;
//             size_t chunkSize = _min(4096, diff);
//             // Log.info("%s [%d]: chunksize - %d\r\n", __FILE__, __LINE__, chunkSize);
//             // delay(10);
//             uint16_t res = file.write(in_buffer + bytesWritten, chunkSize);
//             if (res != chunkSize)
//             {
//                 file.close();
//                 SPIFFS.format();
//                 return bytesWritten;
//             }
//             bytesWritten += chunkSize;
//         }
//         file.close();
//         return bytesWritten;
//     }
//     else
//     {
//         return 0;
//     }
// }

// /**
//  * @brief Function to check if file exists
//  * @param name filename
//  * @return result - true if exists; false - if not exists
//  */
// bool fs_file_exists(const char *name)
// {
//     if (SPIFFS.exists(name))
//     {
//         return true;
//     }
//     else
//     {
//         return false;
//     }
// }

// /**
//  * @brief Function to delete the file
//  * @param name filename
//  * @return result - true if success; false - if failed
//  */
// bool fs_file_delete(const char *name)
// {
//     if (SPIFFS.exists(name))
//     {
//         if (SPIFFS.remove(name))
//         {
//             return true;
//         }
//         else
//         {
//             return false;
//         }
//     }
//     else
//     {
//         return true;
//     }
// }

// /**
//  * @brief Function to rename the file
//  * @param old_name old filename
//  * @param new_name new filename
//  * @return result - true if success; false - if failed
//  */
// bool fs_file_rename(const char *old_name, const char *new_name)
// {
//     if (SPIFFS.exists(old_name))
//     {
//         bool res = SPIFFS.rename(old_name, new_name);
//         if (res)
//         {
//             return true;
//         }
//         else
//             return false;
//     }
//     else
//     {
//         return false;
//     }
// }