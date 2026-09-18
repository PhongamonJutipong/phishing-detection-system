/**
 * Logger ฝั่งส่วนขยาย (แผนภาพลำดับงาน Show Risk Summary: UserInterface -> Logger.logInfo)
 */
class Logger {
  static PREFIX = "[Phishing Detector]";

  static logInfo(msg, ...args) {
    console.info(Logger.PREFIX, msg, ...args);
  }

  static logError(msg, ...args) {
    console.error(Logger.PREFIX, msg, ...args);
  }
}
