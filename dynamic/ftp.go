package dynamic

import (
	"fmt"
	"time"

	"github.com/jlaffaye/ftp"
)

type FtpClient struct {
	conn *ftp.ServerConn
}

func FtpConnect(addr string, port int16) (*FtpClient, error) {
	addr = fmt.Sprintf("%s:%d", addr, port)
	conn, err := ftp.Dial(addr, ftp.DialWithTimeout(5*time.Second))
	if err != nil {
		return nil, err
	}

	return &FtpClient{
		conn: conn,
	}, nil
}

func (ftp *FtpClient) GetFile(from string, to string) {

}

func (ftp *FtpClient) SendFile(from string, to string) {

}
